# LarkEdit

Python製の動画編集ソフト

## ディレクトリ構造

```plaintext
LarkEdit/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ CMakeLists.txt            # ffmpeg_binding ビルド
├─ src/
│  └─ larkedit/
│     ├─ __init__.py
│     ├─ app.py              # QApplication/メインループ
│     ├─ gui/
│     │   ├─ __init__.py
│     │   ├─ main_window.py
│     │   ├─ timeline.py
│     │   ├─ preview.py
│     │   ├─ controls/
│     │   │   ├─ media_browser.py
│     │   │   └─ ...
│     │   └─ qml/            # （任意）QML 追加時
│     ├─ core/
│     │   ├─ __init__.py
│     │   ├─ project.py      # *.larkproj
│     │   ├─ media_manager.py
│     │   ├─ command.py      # BaseCommand / UndoStack
│     │   ├─ render_queue.py
│     │   ├─ compositor.py   # CPU/GPU 合成 (PyOpenGL 等)
│     │   └─ services/       # 抽象サービスインターフェース
│     ├─ encoding/
│     │   ├─ __init__.py
│     │   ├─ presets.py
│     │   └─ ffmpeg_binding/     # C/C++ ソース + Python ラッパ
│     │       └─ encoder.cpp
│     ├─ extensions/
│     │   ├─ __init__.py
│     │   ├─ api.py         # 公開インターフェース (@hook)
│     │   ├─ manager.py     # プラグイン検出・ライフサイクル
│     │   └─ builtin/
│     │       ├─ text_draw/
│     │       │   ├─ plugin.py
│     │       │   └─ qml/
│     │       ├─ shape_draw/
│     │       └─ ...
│     ├─ themes/
│     │   ├─ default/
│     │   │   └─ theme.qss
│     │   └─ dark/
│     ├─ i18n/
│     │   ├─ en_US/
│     │   │   └─ messages.qm
│     │   └─ ja_JP/
│     ├─ utils/
│     │   ├─ config.py
│     │   ├─ paths.py
│     │   └─ logger.py
│     └─ cli.py             # `python -m larkedit` or console_script
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ plugins/
├─ docs/
│  ├─ index.md
│  └─ ...
└─ resources/               # 非 Python: アイコン, 効果音, 既定テンプレート
```
