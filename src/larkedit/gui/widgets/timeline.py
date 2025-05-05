from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QColor, QPaintEvent
from PySide6.QtWidgets import QWidget, QScrollArea

from ...core.project import Project, Track


class _TimelineCanvas(QWidget):
    """
    Timeline の実描画部。今は非常に簡素な矩形描画のみ。
    """

    TRACK_HEIGHT = 40
    PIXELS_PER_MS = 0.02  # 50 ms = 1 px

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._project = project
        self.setMinimumHeight(self._calc_total_height())

    # --- paint ---
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        for t in self._project.timeline.tracks:
            self._draw_track(p, t)
        p.end()

    def _draw_track(self, painter: QPainter, track: Track) -> None:
        y = track.index * self.TRACK_HEIGHT
        # 背景
        painter.fillRect(QRect(0, y, self.width(), self.TRACK_HEIGHT), QColor("#333"))
        # クリップ
        for clip in track.clips:
            x = int(clip.start_ms * self.PIXELS_PER_MS)
            w = int(clip.duration_ms * self.PIXELS_PER_MS)
            painter.fillRect(QRect(x, y + 4, w, self.TRACK_HEIGHT - 8), QColor("#6699cc"))

    # --- utils ---
    def _calc_total_height(self) -> int:
        tracks = len(self._project.timeline.tracks)
        return max(200, tracks * self.TRACK_HEIGHT)

    def set_project(self, project: Project) -> None:
        self._project = project
        self.setMinimumHeight(self._calc_total_height())
        self.update()


class TimelineWidget(QScrollArea):
    """
    スクロール可能なタイムラインビュー。
    """

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelineWidget")
        self.setWidgetResizable(True)

        self._canvas = _TimelineCanvas(project, self)
        self.setWidget(self._canvas)

    # ---
    def set_project(self, project: Project) -> None:
        self._canvas.set_project(project)
