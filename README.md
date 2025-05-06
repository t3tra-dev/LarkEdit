# LarkEdit

Python製の動画編集ソフト

## アーキテクチャ

- PySide6 で GUI を設計
- FFmpeg API を pybind11 でラップ、エンコーダー等に利用
- データストリームは主に numpy 経由

## ディレクトリ構造

```plaintext
LarkEdit
├── .flake8
├── .gitignore
├── .python-version
├── .vscode
│   ├── c_cpp_properties.json
│   └── settings.json
├── CMakeLists.txt
├── README.md
├── example_output
│   └── out_full.mp4
├── examples
│   └── ffmpeg_binding.py
├── pyproject.toml
└── src
    ├── README.md
    └── larkedit
        ├── __init__.py
        ├── __main__.py
        ├── app.py
        ├── cli.py
        ├── core
        │   ├── __init__.py
        │   ├── command.py
        │   ├── compositor.py
        │   ├── media_manager.py
        │   ├── project.py
        │   ├── render_queue.py
        │   └── services
        ├── encoding
        │   ├── __init__.py
        │   ├── ffmpeg_binding
        │   │   ├── CMakeLists.txt
        │   │   ├── __init__.py
        │   │   ├── binding.cpp
        │   │   ├── common.hpp
        │   │   ├── compositor.cpp
        │   │   ├── compositor.hpp
        │   │   ├── encoder.cpp
        │   │   ├── encoder.hpp
        │   │   ├── encoder.pyi
        │   │   └── thread_queue.hpp
        │   └── presets.py
        ├── extensions
        │   ├── __init__.py
        │   ├── api.py
        │   ├── builtin
        │   │   ├── shape_draw
        │   │   └── text_draw
        │   │       ├── plugin.py
        │   │       └── qml
        │   └── manager.py
        ├── gui
        │   ├── __init__.py
        │   ├── controls
        │   │   └── media_browser.py
        │   ├── editor.py
        │   ├── main_window.py
        │   ├── qml
        │   ├── welcome.py
        │   └── widgets
        │       ├── media_pool.py
        │       ├── preview.py
        │       ├── property_editor.py
        │       └── timeline.py
        ├── i18n
        │   ├── en_US
        │   │   └── messages.qm
        │   └── ja_JP
        ├── themes
        │   ├── dark
        │   └── default
        │       └── theme.qss
        └── utils
            ├── config.py
            ├── logger.py
            └── paths.py
```
