#include "compositor.hpp"
#include <algorithm>

Compositor::Compositor(int w, int h) : _w(w), _h(h) {}
VideoFrame Compositor::compose(const std::vector<VideoFrame>& layers) {
    VideoFrame result{_w, _h, layers.empty() ? 0 : layers[0].pts, std::vector<uint8_t>(_w*_h*4, 0)};
    // αブレンド (premultiplied αは省略/最適化余地大)
    for (const auto& l : layers) {
        for (size_t i = 0; i < result.rgba.size(); i += 4) {
            float a = l.rgba[i+3] / 255.f;
            result.rgba[i+0] = static_cast<uint8_t>(l.rgba[i+0]*a + result.rgba[i+0]*(1-a));
            result.rgba[i+1] = static_cast<uint8_t>(l.rgba[i+1]*a + result.rgba[i+1]*(1-a));
            result.rgba[i+2] = static_cast<uint8_t>(l.rgba[i+2]*a + result.rgba[i+2]*(1-a));
            result.rgba[i+3] = 255;
        }
    }
    return result;
}
