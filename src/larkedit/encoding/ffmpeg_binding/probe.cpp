#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "common.hpp" // ff_err2str / FFMpegInit
extern "C"
{
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswscale/swscale.h>
#include <libavutil/version.h>
}

#define FFMPEG_VERSION_GTE_5 (LIBAVUTIL_VERSION_MAJOR >= 57)

namespace py = pybind11;

// --- helpers ---
struct ScopedFmtCtx
{
    AVFormatContext *ctx{nullptr};
    ~ScopedFmtCtx()
    {
        if (ctx)
            avformat_close_input(&ctx);
    }
};

struct ScopedCodecCtx
{
    AVCodecContext *ctx{nullptr};
    ~ScopedCodecCtx()
    {
        if (ctx)
            avcodec_free_context(&ctx);
    }
};

inline void throw_if(int err, const char *msg)
{
    if (err < 0)
        throw std::runtime_error(std::string(msg) + ": " + ff_err2str(err));
}

// --- MediaInfo ---
py::dict probe(const std::string &file)
{
    static FFMpegInit _once;

    ScopedFmtCtx fmt;
    throw_if(avformat_open_input(&fmt.ctx, file.c_str(), nullptr, nullptr),
             "avformat_open_input");
    throw_if(avformat_find_stream_info(fmt.ctx, nullptr),
             "avformat_find_stream_info");

    py::dict info;
    info["duration_ms"] = fmt.ctx->duration != AV_NOPTS_VALUE
                              ? static_cast<int64_t>(fmt.ctx->duration / (AV_TIME_BASE / 1000))
                              : -1;

    // --- streams ---
    for (unsigned i = 0; i < fmt.ctx->nb_streams; ++i)
    {
        AVStream *st = fmt.ctx->streams[i];
        if (st->codecpar->codec_type == AVMEDIA_TYPE_VIDEO && !info.contains("video"))
        {
            AVRational fr = st->avg_frame_rate.num ? st->avg_frame_rate : st->r_frame_rate;
            double fps = fr.num && fr.den ? static_cast<double>(fr.num) / fr.den : 0.0;
            py::dict v;
            v["width"] = st->codecpar->width;
            v["height"] = st->codecpar->height;
            v["fps"] = fps;
            info["video"] = v;
        }
        else if (st->codecpar->codec_type == AVMEDIA_TYPE_AUDIO && !info.contains("audio"))
        {
            py::dict a;
            a["sample_rate"] = st->codecpar->sample_rate;
#if FFMPEG_VERSION_GTE_5
            a["channels"] = st->codecpar->ch_layout.nb_channels;
#else
            a["channels"] = st->codecpar->channels;
#endif
            info["audio"] = a;
        }
    }
    return info;
}

// --- extract frame (RGBA) ---
py::tuple extract_rgba_frame(const std::string &file,
                             int64_t ms,
                             int max_w,
                             int max_h)
{
    static FFMpegInit _once;

    // --- open / find video stream ---
    ScopedFmtCtx fmt;
    throw_if(avformat_open_input(&fmt.ctx, file.c_str(), nullptr, nullptr),
             "avformat_open_input");
    throw_if(avformat_find_stream_info(fmt.ctx, nullptr),
             "avformat_find_stream_info");

    int v_idx = av_find_best_stream(fmt.ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    if (v_idx < 0)
        throw std::runtime_error("video stream not found");

    AVStream *v_st = fmt.ctx->streams[v_idx];
    const AVCodec *codec = avcodec_find_decoder(v_st->codecpar->codec_id);
    if (!codec)
        throw std::runtime_error("decoder not found");

    ScopedCodecCtx vctx;
    vctx.ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(vctx.ctx, v_st->codecpar);
    throw_if(avcodec_open2(vctx.ctx, codec, nullptr), "avcodec_open2");

    // --- seek ---
    int64_t ts = ms * v_st->time_base.den / (1000LL * v_st->time_base.num);
    av_seek_frame(fmt.ctx, v_idx, ts, AVSEEK_FLAG_BACKWARD);
    avcodec_flush_buffers(vctx.ctx);

    // --- decode first frame ---
    AVPacket *pkt = av_packet_alloc();
    AVFrame *frm = av_frame_alloc();
    bool got = false;
    while (av_read_frame(fmt.ctx, pkt) >= 0)
    {
        if (pkt->stream_index != v_idx)
        {
            av_packet_unref(pkt);
            continue;
        }
        throw_if(avcodec_send_packet(vctx.ctx, pkt), "send_packet");
        av_packet_unref(pkt);
        while (avcodec_receive_frame(vctx.ctx, frm) == 0)
        {
            got = true;
            break;
        }
        if (got)
            break;
    }
    av_packet_free(&pkt);
    if (!got)
    {
        av_frame_free(&frm);
        throw std::runtime_error("decode failed");
    }

    // --- scale & RGBA ---
    int dst_w = frm->width, dst_h = frm->height;
    if (max_w > 0 && max_h > 0)
    {
        double scale = std::min(1.0, std::min(static_cast<double>(max_w) / frm->width,
                                              static_cast<double>(max_h) / frm->height));
        dst_w = static_cast<int>(frm->width * scale);
        dst_h = static_cast<int>(frm->height * scale);
    }

    SwsContext *sws = sws_getContext(frm->width, frm->height,
                                     static_cast<AVPixelFormat>(frm->format),
                                     dst_w, dst_h, AV_PIX_FMT_RGBA,
                                     SWS_BILINEAR, nullptr, nullptr, nullptr);
    if (!sws)
    {
        av_frame_free(&frm);
        throw std::runtime_error("sws_getContext");
    }

    std::vector<uint8_t> rgba(dst_w * dst_h * 4);
    uint8_t *dst_data[1] = {rgba.data()};
    int dst_linesize[1] = {dst_w * 4};

    sws_scale(sws, frm->data, frm->linesize, 0, frm->height, dst_data, dst_linesize);
    sws_freeContext(sws);
    av_frame_free(&frm);

    return py::make_tuple(dst_w, dst_h,
                          py::bytes(reinterpret_cast<char *>(rgba.data()),
                                    rgba.size()));
}

// --- module ---
PYBIND11_MODULE(probe, m)
{
    m.doc() = "FFmpeg utility (probing & thumbnail) for LarkEdit";

    m.def("probe", &probe,
          py::arg("file"),
          "Return media information dict");
    m.def("extract_rgba_frame", &extract_rgba_frame,
          py::arg("file"),
          py::arg("ms") = 0,
          py::arg("max_w") = 256,
          py::arg("max_h") = 256,
          R"pbdoc(
              Extract one frame at given milliseconds.
              Returns (width, height, raw_rgba_bytes).
          )pbdoc");
}
