#pragma once
#include <memory>
#include <thread>
#include <atomic>
#include "thread_queue.hpp"
#include "compositor.hpp"
#include "common.hpp"

extern "C" {
    #include <libavcodec/avcodec.h>
    #include <libavformat/avformat.h>
    #include <libswscale/swscale.h>
    #include <libswresample/swresample.h>
}

struct AudioSamples {
    int64_t pts;            // ミリ秒
    std::vector<float> pcm; // interleaved float32
};

class MediaEncoder {
public:
    MediaEncoder(const std::string& filename,
                 int width, int height, int fps,
                 int sr = 48000, int ch = 2,
                 const std::string& vcodec = "libx264",
                 const std::string& acodec = "aac",
                 size_t queue_cap = 32);

    void start();                           // スレッド開始
    void submit_video(const VideoFrame& v); // キューに積む
    void submit_audio(const AudioSamples& a);
    void finish();                          // flush & join
    ~MediaEncoder();

private:
    void _encode_loop();
    void _init_video_stream();
    void _init_audio_stream();
    void _encode_video(const VideoFrame& v);
    void _encode_audio(const AudioSamples& a);
    void _flush();

    // FFmpeg
    AVFormatContext* _oc{nullptr};
    AVStream* _vst{nullptr};
    AVStream* _ast{nullptr};
    AVCodecContext* _vctx{nullptr};
    AVCodecContext* _actx{nullptr};
    SwsContext* _sws{nullptr};
    SwrContext* _swr{nullptr};
    int64_t _last_video_dts{AV_NOPTS_VALUE};  // DTS単調増加を保証するための前回値

    // cfg
    std::string _filename;
    int _w, _h, _fps, _sr, _ch;

    // threading
    ThreadQueue<std::variant<VideoFrame, AudioSamples>> _queue;
    std::thread _worker;
    std::atomic<bool> _running{false};
};
