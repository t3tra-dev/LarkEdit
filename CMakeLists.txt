# ------------------------------------
# LarkEdit C++ / pybind11 バインディング
# ------------------------------------

cmake_minimum_required(VERSION 4.0.1)
project(larkedit_encoder LANGUAGES C CXX)

# C++17 を使用
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 1) pybind11 を取得
# - pip でインストール済み (pyproject.toml) の CONFIG パッケージ
find_package(pybind11 CONFIG REQUIRED)

# 2) FFmpeg ライブラリを検出
# - Linux/macOS: pkg-config
# - Windows    : FFMPEG_ROOT 指定など fallback を実装しておく
find_package(PkgConfig REQUIRED)
pkg_check_modules(FFMPEG REQUIRED IMPORTED_TARGET
    libavcodec
    libavformat
    libavutil
    libswscale
    libswresample
)

# 3) Python 拡張モジュールのビルド
# - 出力名は 'encoder' -> Python名は larkedit.encoding.ffmpeg_binding.encoder
pybind11_add_module(encoder
    src/larkedit/encoding/ffmpeg_binding/encoder.cpp
)

target_link_libraries(encoder PRIVATE
    PkgConfig::FFMPEG
)

# 必要なら FFmpeg の include パスを追加
target_include_directories(encoder PRIVATE
    ${FFMPEG_INCLUDE_DIRS}
)

# 4) インストール先
# - scikit-build-core が ${SKBUILD_PLATLIB_DIR} を定義
install(TARGETS encoder
    LIBRARY DESTINATION "${SKBUILD_PLATLIB_DIR}/larkedit/encoding/ffmpeg_binding"
)
