#pragma once
#include <string>
#include <stdexcept>
extern "C" {
    #include <libavformat/avformat.h>
}

inline std::string ff_err2str(int err) {
    char buf[AV_ERROR_MAX_STRING_SIZE];
    av_strerror(err, buf, sizeof(buf));
    return std::string(buf);
}

struct FFMpegInit {
    FFMpegInit()  { av_log_set_level(AV_LOG_ERROR); avformat_network_init(); }
    ~FFMpegInit() { avformat_network_deinit();      }
};
