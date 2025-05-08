from __future__ import annotations

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout

from ...core.project import Project
from .track import TrackWidget


class TimelineWidget(QScrollArea):
    """
    QScrollArea
        └─ _content (QWidget)
            └─ QVBoxLayout
                ├─ TrackWidget 0
                ├─ TrackWidget 1
                └─ ...
    """

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelineWidget")
        self.setWidgetResizable(True)

        self._project = project
        self._content = QWidget()
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)

        self.setWidget(self._content)
        self._track_widgets: list[TrackWidget] = []

        self._populate()

    # --- utils ---
    def _populate(self) -> None:
        # 既存ウィジェット除去
        for tw in self._track_widgets:
            self._vbox.removeWidget(tw)
            tw.deleteLater()
        self._track_widgets.clear()

        # Project の Track をウィジェット化
        for t in sorted(self._project.timeline.tracks, key=lambda x: x.index):
            tw = TrackWidget(self._project, t, self._content)
            tw.clip_added.connect(self._on_clip_added)
            self._vbox.addWidget(tw)
            self._track_widgets.append(tw)

        # スペーサー
        self._vbox.addStretch()

    # --- slots ---
    def _on_clip_added(self) -> None:
        # Clip 追加時に全トラック再描画
        for tw in self._track_widgets:
            tw.update()

    # --- API ---
    def set_project(self, project: Project) -> None:
        self._project = project
        self._populate()
