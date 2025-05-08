from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSplitter, QToolBar, QVBoxLayout, QWidget

from ..core.project import Project, Track
from .widgets.media_pool import MediaPoolWidget
from .widgets.preview import PreviewWidget
from .widgets.property_editor import PropertyEditorWidget
from .widgets.timeline import TimelineWidget


class EditorPage(QWidget):
    """```
    ┌───────────────────────────────────────────────┐
    │ MediaPool │   Preview   │  PropertyEditor     │  ← QSplitter (H)
    └───────────────────────────────────────────────┘
    ┌───────────────────────────────────────────────┐
    │                 Timeline                      │
    └───────────────────────────────────────────────┘
    ```"""

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorPage")

        self._project = project

        # --- Toolbar ---
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        # 例: メディア読み込み / Undo / Redo
        import_act = QAction("メディアを読み込む…", self)
        undo_act = QAction("Undo", self)
        redo_act = QAction("Redo", self)
        toolbar.addAction(import_act)
        toolbar.addSeparator()
        toolbar.addAction(undo_act)
        toolbar.addAction(redo_act)

        # --- レイアウト ---
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(toolbar)

        top_split = QSplitter(Qt.Orientation.Horizontal, self)
        self._media_pool = MediaPoolWidget(project, self)
        self._preview = PreviewWidget(project, self)
        self._prop_editor = PropertyEditorWidget(project, self)

        top_split.addWidget(self._media_pool)
        top_split.addWidget(self._preview)
        top_split.addWidget(self._prop_editor)
        top_split.setStretchFactor(1, 3)  # プレビューを広めに
        top_split.setSizes([200, 600, 250])  # type: ignore

        vbox.addWidget(top_split)

        self._timeline = TimelineWidget(project, self)
        vbox.addWidget(self._timeline)

    # --- API ---
    def set_project(self, project: Project) -> None:
        """Welcome から戻って別プロジェクトを開いた場合に再バインドする"""
        self._project = project
        self._media_pool.set_project(project)
        self._preview.set_project(project)
        self._prop_editor.set_project(project)
        self._timeline.set_project(project)

        # 最低 1 トラック
        if not self._project.timeline.tracks:
            self._project.timeline.add_track(Track(index=0, name="V1"))
        self._timeline.set_project(self._project)
