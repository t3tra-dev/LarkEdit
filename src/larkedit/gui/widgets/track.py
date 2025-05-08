from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import QRect, QMimeData, Signal
from PySide6.QtGui import QPainter, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget

from ...core.project import Project, Track, AddClipCommand
from ...core.command import UndoStack
from .media_pool import MIME_ASSET_PATH

__all__ = ["TrackWidget"]


class TrackWidget(QWidget):
    """
    1 トラックを表す行ウィジェット。
    * 背景・ヘッダ・クリップ矩形を自前でペイント
    * MediaPool からの D&D を受け取り AddClipCommand を発行
    """

    clip_added = Signal()  # タイムライン全体の再描画要求用

    TRACK_HEIGHT = 40
    PIXELS_PER_MS = 0.02

    def __init__(self, project: Project, track: Track, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._project = project
        self._track = track
        self.setObjectName("TrackWidget")
        self.setFixedHeight(self.TRACK_HEIGHT)
        self.setAcceptDrops(True)

    # --- D&D ---
    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasFormat(MIME_ASSET_PATH):
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        md: QMimeData = e.mimeData()
        path = Path(bytes(md.data(MIME_ASSET_PATH).data()).decode())
        asset = next(
            (a for a in self._project.timeline.track(self._track.index).clips or []
             for a in [a.asset] if a.path == path),
            None,
        )
        if asset is None:
            # MediaPool がまだ Project に asset を登録していない場合は捜す
            for t in self._project.timeline.tracks:
                for c in t.clips:
                    if c.asset.path == path:
                        asset = c.asset
                        break
        if asset is None:  # asset 未登録ならスキップ
            return

        start_ms = int(e.position().x() / self.PIXELS_PER_MS)
        if not self._project.undo_stack:
            self._project.undo_stack = UndoStack()

        cmd = AddClipCommand(
            self._project,
            track_index=self._track.index,
            asset=asset,
            start_ms=start_ms,
        )
        self._project.undo_stack.push(cmd)
        self.clip_added.emit()
        e.acceptProposedAction()

    # --- paint ---
    def paintEvent(self, _):
        p = QPainter(self)
        # 背景
        p.fillRect(self.rect(), QColor("#222"))
        # クリップ
        for clip in self._track.clips:
            x = int(clip.start_ms * self.PIXELS_PER_MS)
            w = int(clip.duration_ms * self.PIXELS_PER_MS)
            p.fillRect(QRect(x, 4, w, self.height() - 8), QColor("#6699cc"))
        p.end()

    # --- utils ---
    def set_track(self, track: Track) -> None:
        self._track = track
        self.update()
