add_library(larkedit_encoder MODULE
    binding.cpp
    encoder.cpp
    compositor.cpp
)

target_link_libraries(larkedit_encoder
    PRIVATE
    pybind11::module
    PkgConfig::FFMPEG
)

set_target_properties(larkedit_encoder PROPERTIES
    OUTPUT_NAME encoder
    PREFIX ""
) # -> encoder.so / pyd
install(TARGETS larkedit_encoder
    LIBRARY DESTINATION "${SKBUILD_PLATLIB_DIR}/larkedit/encoding/ffmpeg_binding"
)

add_library(larkedit_probe MODULE probe.cpp)
target_link_libraries(larkedit_probe PRIVATE pybind11::module PkgConfig::FFMPEG)

set_target_properties(larkedit_probe PROPERTIES
    OUTPUT_NAME probe
    PREFIX ""
) # -> probe.so / pyd
install(TARGETS larkedit_probe
    LIBRARY DESTINATION "${SKBUILD_PLATLIB_DIR}/larkedit/encoding/ffmpeg_binding"
)
