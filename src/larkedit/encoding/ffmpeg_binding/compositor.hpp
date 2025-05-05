#pragma once
#include <vector>
#include <cstdint>
struct VideoFrame {
    int width, height;
    int64_t pts;                 // ミリ秒
    std::vector<uint8_t> rgba;   // RGBA 実フレーム
};

class Compositor {
public:
    Compositor(int canvas_w, int canvas_h);
    VideoFrame compose(const std::vector<VideoFrame>& layers); // 上から順にブレンド
private:
    int _w, _h;
};
