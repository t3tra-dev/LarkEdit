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
