# ------------------------------------
# LarkEdit C++ / pybind11 バインディング
# ------------------------------------

cmake_minimum_required(VERSION 4.0.1)
project(larkedit_encoder LANGUAGES C CXX)

# C++17 を使用
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)  # Python 拡張は必須

# 1) pybind11 を取得
# - pip でインストール済み (pyproject.toml) の CONFIG パッケージ
find_package(pybind11 CONFIG REQUIRED)

# 2) FFmpeg ライブラリを検出
# - Linux/macOS: pkg-config
# - Windows    : FFMPEG_ROOT 指定など fallback を実装しておく
find_package(PkgConfig REQUIRED)
pkg_check_modules(FFMPEG IMPORTED_TARGET
    libavcodec
    libavformat
    libavutil
    libswscale
    libswresample
)

if(NOT FFMPEG_FOUND)
    if(DEFINED ENV{FFMPEG_ROOT})
        message(STATUS "Using FFMPEG_ROOT=$ENV{FFMPEG_ROOT}")
        list(APPEND CMAKE_PREFIX_PATH "$ENV{FFMPEG_ROOT}")
        pkg_check_modules(FFMPEG REQUIRED IMPORTED_TARGET
            libavcodec
            libavformat
            libavutil
            libswscale
            libswresample
        )
    else()
        message(FATAL_ERROR "FFmpeg development libraries not found.\n"
            "Install via package manager, vcpkg, or set FFMPEG_ROOT.")
    endif()
endif()

# FFmpeg の include パスをサブディレクトリにも伝える
set(FFMPEG_INCLUDE_DIRS ${FFMPEG_INCLUDE_DIRS} CACHE INTERNAL "")

add_subdirectory(src/larkedit/encoding/ffmpeg_binding)
