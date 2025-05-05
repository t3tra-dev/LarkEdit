from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QPushButton,
)

from ...core.project import MediaAsset, MediaType, Project


class MediaPoolWidget(QWidget):
    """
    読み込んだメディアを列挙。ドラッグ＆ドロップでタイムラインへもっていける想定。
    """

    asset_added = Signal(MediaAsset)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MediaPoolWidget")
        self._project = project

        vbox = QVBoxLayout(self)
        add_btn = QPushButton("+ メディアを追加...")
        add_btn.clicked.connect(self._choose_file)
        vbox.addWidget(add_btn)

        self._list = QListWidget()
        vbox.addWidget(self._list)

    # ---
    def set_project(self, project: Project) -> None:
        self._project = project
        self._list.clear()

    def _choose_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "メディアを選択", "", "Media Files (*.mp4 *.mov *.png *.jpg *.wav)"
        )
        for p in paths:
            self._import_media(Path(p))

    def _import_media(self, path: Path) -> None:
        # TODO: メディア情報を FFprobe 等で取得して duration/ms 判定
        asset = MediaAsset(path, MediaType.VIDEO, duration_ms=10_000)
        item = QListWidgetItem(path.name)
        item.setData(Qt.ItemDataRole.UserRole, asset)
        self._list.addItem(item)
        self.asset_added.emit(asset)
