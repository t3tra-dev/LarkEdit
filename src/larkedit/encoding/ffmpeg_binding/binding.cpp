#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "encoder.hpp"
#include "compositor.hpp"

namespace py = pybind11;

PYBIND11_MODULE(encoder, m) {
    m.doc() = "FFmpeg encoder binding for LarkEdit";

    /* --- Structs --- */
    py::class_<VideoFrame>(m, "VideoFrame")
        .def(py::init([](int width, int height, int64_t pts, py::bytes rgba) {
            // py::bytesからstd::vector<uint8_t>に変換
            py::buffer_info info(py::buffer(rgba).request());
            auto* ptr = static_cast<uint8_t*>(info.ptr);
            return VideoFrame{
                width,
                height,
                pts,
                std::vector<uint8_t>(ptr, ptr + info.size)
            };
        }))
        .def_readwrite("width",  &VideoFrame::width)
        .def_readwrite("height", &VideoFrame::height)
        .def_readwrite("pts",    &VideoFrame::pts)
        .def_readwrite("rgba",   &VideoFrame::rgba);

    py::class_<AudioSamples>(m, "AudioSamples")
        .def(py::init<int64_t, std::vector<float>>())
        .def_readwrite("pts",  &AudioSamples::pts)
        .def_readwrite("pcm",  &AudioSamples::pcm);

    /* --- Compositor --- */
    py::class_<Compositor>(m, "Compositor")
        .def(py::init<int,int>())
        .def("compose", &Compositor::compose);

    /* --- MediaEncoder --- */
    py::class_<MediaEncoder>(m, "MediaEncoder")
        .def(py::init<const std::string&,int,int,int,int,int,
                      const std::string&,const std::string&, size_t>(),
             py::arg("filename"), py::arg("width"), py::arg("height"), py::arg("fps"),
             py::arg("sample_rate")=48000, py::arg("channels")=2,
             py::arg("video_codec")="libx264", py::arg("audio_codec")="aac",
             py::arg("queue_cap")=32)
        .def("start", &MediaEncoder::start)
        .def("submit_video", [](MediaEncoder& self, py::array_t<uint8_t, py::array::c_style> arr, int64_t pts){
                py::gil_scoped_release no_gil;
                if (arr.ndim()!=3 || arr.shape(2)!=4)
                    throw std::runtime_error("Expected HxWx4 RGBA");
                VideoFrame vf{
                    static_cast<int>(arr.shape(1)),
                    static_cast<int>(arr.shape(0)),
                    pts,
                    std::vector<uint8_t>(arr.data(), arr.data()+arr.size())
                };
                self.submit_video(vf);
            })
        .def("submit_audio", [](MediaEncoder& self, py::array_t<float, py::array::c_style> arr, int64_t pts){
                py::gil_scoped_release no_gil;
                AudioSamples as{pts, std::vector<float>(arr.data(), arr.data()+arr.size())};
                self.submit_audio(as);
            })
        .def("finish", &MediaEncoder::finish);
}
