#include "encoder.hpp"

#include <cstring>          // std::memcpy
#include <utility>          // std::move
#include <variant>

extern "C" {
    #include <libavutil/opt.h>
    #include <libavutil/version.h>
}

#define FFMPEG_VERSION_GTE_5 (LIBAVUTIL_VERSION_MAJOR >= 57)

namespace {

inline void throw_if_error(int err, const char* msg) {
    if (err < 0) {
        throw std::runtime_error(std::string(msg) + ": " + ff_err2str(err));
    }
}

/* --- RAII ヘルパ --- */
struct FrameDeleter {
    void operator()(AVFrame* f) const noexcept { if (f) av_frame_free(&f); }
};
using FramePtr = std::unique_ptr<AVFrame, FrameDeleter>;

struct PacketDeleter {
    void operator()(AVPacket* p) const noexcept { if (p) av_packet_free(&p); }
};
using PacketPtr = std::unique_ptr<AVPacket, PacketDeleter>;

// 非推奨APIを回避する
inline AVSampleFormat get_default_sample_fmt(const AVCodec* codec) {
#if FFMPEG_VERSION_GTE_5
    return AV_SAMPLE_FMT_FLTP;
#else
    const enum AVSampleFormat* sample_fmts = codec->sample_fmts;
    return sample_fmts ? sample_fmts[0] : AV_SAMPLE_FMT_FLTP;
#endif
}

}  // namespace

// MediaEncoder 本体
MediaEncoder::MediaEncoder(const std::string& filename,
                           int width,
                           int height,
                           int fps,
                           int sr,
                           int ch,
                           const std::string& vcodec,
                           const std::string& acodec,
                           size_t queue_cap)
    : _queue(queue_cap),
      _filename(filename),
      _w(width),
      _h(height),
      _fps(fps),
      _sr(sr),
      _ch(ch),
      _last_video_dts(AV_NOPTS_VALUE) {
    static FFMpegInit _once;

    /* ---出力コンテキスト --- */
    throw_if_error(
        avformat_alloc_output_context2(&_oc, nullptr, nullptr, filename.c_str()),
        "avformat_alloc_output_context2");

    /* --- 動画ストリーム ---- */
    const AVCodec* vcod = avcodec_find_encoder_by_name(vcodec.c_str());
    if (!vcod) {
        throw std::runtime_error("Video codec '" + vcodec + "' not found");
    }
    _vst = avformat_new_stream(_oc, vcod);
    if (!_vst) throw std::runtime_error("avformat_new_stream(v) failed");

    _vctx = avcodec_alloc_context3(vcod);
    if (!_vctx) throw std::runtime_error("avcodec_alloc_context3(v) failed");

    _vctx->codec_id  = vcod->id;
    _vctx->pix_fmt   = AV_PIX_FMT_YUV420P;
    _vctx->width     = width;
    _vctx->height    = height;
    _vctx->time_base = AVRational{1, fps};
    _vctx->framerate = AVRational{fps, 1};
    _vctx->bit_rate  = 4'000'000;
    if (vcod->id == AV_CODEC_ID_H264) {
        av_opt_set(_vctx->priv_data, "preset", "veryfast", 0);
        av_opt_set(_vctx->priv_data, "crf", "23", 0);
    }
    throw_if_error(avcodec_open2(_vctx, vcod, nullptr), "avcodec_open2(v)");
    throw_if_error(avcodec_parameters_from_context(_vst->codecpar, _vctx),
                   "avcodec_parameters_from_context(v)");

    /* --- オーディオストリーム (任意) --- */
    if (!acodec.empty()) {
        const AVCodec* acod = avcodec_find_encoder_by_name(acodec.c_str());
        if (!acod) {
            throw std::runtime_error("Audio codec '" + acodec + "' not found");
        }
        _ast = avformat_new_stream(_oc, acod);
        if (!_ast) throw std::runtime_error("avformat_new_stream(a) failed");

        _actx = avcodec_alloc_context3(acod);
        if (!_actx) throw std::runtime_error("avcodec_alloc_context3(a) failed");

        _actx->sample_rate    = sr;
#if FFMPEG_VERSION_GTE_5
        av_channel_layout_default(&_actx->ch_layout, ch);
#else
        _actx->channel_layout = (ch == 1 ? AV_CH_LAYOUT_MONO : AV_CH_LAYOUT_STEREO);
        _actx->channels       = ch;
#endif
        _actx->sample_fmt     = get_default_sample_fmt(acod);
        _actx->bit_rate       = 128'000;
        _actx->time_base      = AVRational{1, sr};
        throw_if_error(avcodec_open2(_actx, acod, nullptr), "avcodec_open2(a)");
        throw_if_error(avcodec_parameters_from_context(_ast->codecpar, _actx),
                       "avcodec_parameters_from_context(a)");

        /* Resampler: FLT (Python) -> codec fmt */
#if FFMPEG_VERSION_GTE_5
        _swr = swr_alloc();
        if (!_swr) throw std::runtime_error("swr_alloc failed");
        
        av_opt_set_chlayout(_swr, "in_chlayout", &_actx->ch_layout, 0);
        av_opt_set_int(_swr, "in_sample_rate", _actx->sample_rate, 0);
        av_opt_set_sample_fmt(_swr, "in_sample_fmt", AV_SAMPLE_FMT_FLT, 0);
        
        av_opt_set_chlayout(_swr, "out_chlayout", &_actx->ch_layout, 0);
        av_opt_set_int(_swr, "out_sample_rate", _actx->sample_rate, 0);
        av_opt_set_sample_fmt(_swr, "out_sample_fmt", _actx->sample_fmt, 0);
#else
        _swr = swr_alloc_set_opts(
            nullptr,
            _actx->channel_layout,
            _actx->sample_fmt,
            _actx->sample_rate,
            _actx->channel_layout,
            AV_SAMPLE_FMT_FLT,
            _actx->sample_rate,
            0,
            nullptr);
#endif
        if (!_swr || swr_init(_swr) < 0) {
            throw std::runtime_error("swr_init failed");
        }
    }

    /* --- ファイルオープン & ヘッダ --- */
    if (!(_oc->oformat->flags & AVFMT_NOFILE)) {
        throw_if_error(avio_open(&_oc->pb, filename.c_str(), AVIO_FLAG_WRITE),
                       "avio_open");
    }
    throw_if_error(avformat_write_header(_oc, nullptr), "avformat_write_header");

    /* --- 色変換コンテキスト --- */
    _sws = sws_getContext(width,
                          height,
                          AV_PIX_FMT_RGBA,
                          width,
                          height,
                          _vctx->pix_fmt,
                          SWS_BILINEAR,
                          nullptr,
                          nullptr,
                          nullptr);
    if (!_sws) throw std::runtime_error("sws_getContext failed");
}

/* --- */

MediaEncoder::~MediaEncoder() {
    try {
        if (_running) finish();
        if (_sws)  sws_freeContext(_sws);
        if (_swr)  swr_free(&_swr);
        if (_vctx) avcodec_free_context(&_vctx);
        if (_actx) avcodec_free_context(&_actx);
        if (_oc) {
            if (!(_oc->oformat->flags & AVFMT_NOFILE) && _oc->pb) {
                avio_closep(&_oc->pb);
            }
            avformat_free_context(_oc);
        }
    } catch (...) {
        // デストラクタでは例外を飛ばさない
    }
}

/* --- */

void MediaEncoder::start() {
    if (_running) return;
    _running = true;
    _worker  = std::thread(&MediaEncoder::_encode_loop, this);
}

void MediaEncoder::submit_video(const VideoFrame& v) {
    if (!_running) throw std::runtime_error("Encoder not started");
    _queue.push(v);
}

void MediaEncoder::submit_audio(const AudioSamples& a) {
    if (!_running) throw std::runtime_error("Encoder not started");
    if (!_actx)    return;  // Audio 無効
    _queue.push(a);
}

void MediaEncoder::finish() {
    if (!_running) return;
    _queue.close();
    if (_worker.joinable()) _worker.join();
    _flush();
    throw_if_error(av_write_trailer(_oc), "av_write_trailer");
    _running = false;
}

/* --- */
/* 内部スレッド */
/* --- */

void MediaEncoder::_encode_loop() {
    while (auto v = _queue.pop()) {
        std::visit(
            [&](auto&& msg) {
                using T = std::decay_t<decltype(msg)>;
                if constexpr (std::is_same_v<T, VideoFrame>)
                    _encode_video(msg);
                else if constexpr (std::is_same_v<T, AudioSamples>)
                    _encode_audio(msg);
            },
            *v);
    }
}

/* --- */
/* 映像ペイロード */
/* --- */

void MediaEncoder::_encode_video(const VideoFrame& vf) {
    /* --- RGBA Frame (src) --- */
    FramePtr rgb(av_frame_alloc());
    rgb->format = AV_PIX_FMT_RGBA;
    rgb->width  = _w;
    rgb->height = _h;
    throw_if_error(av_frame_get_buffer(rgb.get(), 0), "av_frame_get_buffer(rgba)");

    std::memcpy(rgb->data[0], vf.rgba.data(), vf.rgba.size());
    rgb->pts = vf.pts * _fps / 1000;  // ms -> time_base

    /* --- YUV420 (dst) --- */
    FramePtr yuv(av_frame_alloc());
    yuv->format = _vctx->pix_fmt;
    yuv->width  = _w;
    yuv->height = _h;
    throw_if_error(av_frame_get_buffer(yuv.get(), 0), "av_frame_get_buffer(yuv)");

    sws_scale(_sws,
              rgb->data,
              rgb->linesize,
              0,
              _h,
              yuv->data,
              yuv->linesize);
    yuv->pts = rgb->pts;

    /* --- エンコーダへ送信 --- */
    throw_if_error(avcodec_send_frame(_vctx, yuv.get()), "avcodec_send_frame(v)");
    PacketPtr pkt(av_packet_alloc());
    while (true) {
        int ret = avcodec_receive_packet(_vctx, pkt.get());
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) break;
        throw_if_error(ret, "avcodec_receive_packet(v)");
        
        // codec → stream へ時刻変換
        av_packet_rescale_ts(pkt.get(), _vctx->time_base, _vst->time_base);
        pkt->stream_index = _vst->index;
        
        // 同じDTS値が連続しないように調整（単調増加を保証）
        if (pkt->dts != AV_NOPTS_VALUE && _last_video_dts != AV_NOPTS_VALUE && pkt->dts <= _last_video_dts) {
            pkt->dts = _last_video_dts + 1;
            // PTSもDTSより後ろになるよう調整
            if (pkt->pts != AV_NOPTS_VALUE && pkt->pts < pkt->dts) {
                pkt->pts = pkt->dts;
            }
        }
        
        if (pkt->dts != AV_NOPTS_VALUE) {
            _last_video_dts = pkt->dts;
        }
        
        throw_if_error(av_interleaved_write_frame(_oc, pkt.get()),
                       "av_interleaved_write_frame(v)");
        av_packet_unref(pkt.get());
    }
}

/* --- */
/* 音声ペイロード */
/* --- */

void MediaEncoder::_encode_audio(const AudioSamples& a) {
    if (!_actx) return;

    // フレームサイズを取得
    int frame_size = _actx->frame_size > 0 ? _actx->frame_size : 1024;
    
    const int total_samples = static_cast<int>(a.pcm.size() / _ch);
    const uint8_t* in_data = reinterpret_cast<const uint8_t*>(a.pcm.data());
    
    // フレームサイズ単位で処理
    for (int offset = 0; offset < total_samples; offset += frame_size) {
        int current_samples = std::min(frame_size, total_samples - offset);
        if (current_samples <= 0) break;
        
        const uint8_t* in_buf[] = {
            in_data + offset * _ch * sizeof(float),
        };

        /* --- 入力フレーム (FLT / host order) --- */
        FramePtr in(av_frame_alloc());
        in->nb_samples = current_samples;
#if FFMPEG_VERSION_GTE_5
        in->ch_layout = _actx->ch_layout;
#else
        in->channel_layout = _actx->channel_layout;
#endif
        in->format = AV_SAMPLE_FMT_FLT;
        in->sample_rate = _sr;
        throw_if_error(av_frame_get_buffer(in.get(), 0), "av_frame_get_buffer(a-in)");
        std::memcpy(in->data[0], in_buf[0], current_samples * _ch * sizeof(float));
        in->pts = (a.pts + (offset * 1000 / _sr)) * _sr / 1000;  // ms → samples

        /* --- 出力フレーム (codec fmt) --- */
        FramePtr out(av_frame_alloc());
        out->nb_samples = current_samples;
#if FFMPEG_VERSION_GTE_5
        out->ch_layout = _actx->ch_layout;
#else
        out->channel_layout = _actx->channel_layout;
#endif
        out->format = _actx->sample_fmt;
        out->sample_rate = _sr;
        throw_if_error(av_frame_get_buffer(out.get(), 0), "av_frame_get_buffer(a-out)");

        throw_if_error(
            swr_convert(_swr, out->data, current_samples, in_buf, current_samples),
            "swr_convert");

        out->pts = in->pts;

        /* --- エンコーダに送信 --- */
        throw_if_error(avcodec_send_frame(_actx, out.get()), "avcodec_send_frame(a)");
        PacketPtr pkt(av_packet_alloc());
        while (true) {
            int ret = avcodec_receive_packet(_actx, pkt.get());
            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) break;
            throw_if_error(ret, "avcodec_receive_packet(a)");
            
            // codec → stream へ時刻変換
            av_packet_rescale_ts(pkt.get(), _actx->time_base, _ast->time_base);
            pkt->stream_index = _ast->index;
            
            throw_if_error(av_interleaved_write_frame(_oc, pkt.get()),
                        "av_interleaved_write_frame(a)");
            av_packet_unref(pkt.get());
        }
    }
}

/* --- */
/* フラッシュ */
/* --- */

void MediaEncoder::_flush() {
    /* --- Video flush --- */
    throw_if_error(avcodec_send_frame(_vctx, nullptr), "flush video send");
    PacketPtr pkt(av_packet_alloc());
    while (avcodec_receive_packet(_vctx, pkt.get()) == 0) {
        // codec → stream へ時刻変換
        av_packet_rescale_ts(pkt.get(), _vctx->time_base, _vst->time_base);
        pkt->stream_index = _vst->index;
        
        // フラッシュ時も同様にDTS値の単調増加を保証
        if (pkt->dts != AV_NOPTS_VALUE && _last_video_dts != AV_NOPTS_VALUE && pkt->dts <= _last_video_dts) {
            pkt->dts = _last_video_dts + 1;
            // PTSもDTSより後ろになるよう調整
            if (pkt->pts != AV_NOPTS_VALUE && pkt->pts < pkt->dts) {
                pkt->pts = pkt->dts;
            }
        }
        
        if (pkt->dts != AV_NOPTS_VALUE) {
            _last_video_dts = pkt->dts;
        }
        
        throw_if_error(av_interleaved_write_frame(_oc, pkt.get()),
                       "av_interleaved_write_frame(v)");
        av_packet_unref(pkt.get());
    }

    /* --- Audio flush --- */
    if (_actx) {
        throw_if_error(avcodec_send_frame(_actx, nullptr), "flush audio send");
        while (avcodec_receive_packet(_actx, pkt.get()) == 0) {
            // codec → stream へ時刻変換
            av_packet_rescale_ts(pkt.get(), _actx->time_base, _ast->time_base);
            pkt->stream_index = _ast->index;
            
            throw_if_error(av_interleaved_write_frame(_oc, pkt.get()),
                          "av_interleaved_write_frame(a)");
            av_packet_unref(pkt.get());
        }
    }
}
