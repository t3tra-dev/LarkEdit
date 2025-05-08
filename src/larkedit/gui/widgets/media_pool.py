from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QMimeData, Qt
from PySide6.QtGui import QDrag, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.project import MediaAsset, MediaType, Project
from ...utils.media import probe, thumbnail_qpixmap

# 独自 MIME: クリップ追加時に asset.path を渡す
MIME_ASSET_PATH = "application/x-larkedit-asset"


class MediaItemWidget(QWidget):
    """サムネイル + ファイル名"""

    def __init__(
        self, asset: MediaAsset, thumb_size: int = 96, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.asset = asset
        self.setFixedSize(thumb_size + 10, thumb_size + 40)  # 余白込み
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(4)

        # --- サムネイル
        thumb = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        thumb.setFixedSize(thumb_size, thumb_size)
        if asset.media_type == MediaType.IMAGE:
            pm = QPixmap(str(asset.path)).scaled(
                thumb_size,
                thumb_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb.setPixmap(pm)
        else:
            # サムネイルを生成
            pm = thumbnail_qpixmap(asset.path, 0, thumb_size)
            thumb.setPixmap(pm)
        v.addWidget(thumb)

        # --- ファイル名
        name = QLabel(asset.path.name, alignment=Qt.AlignmentFlag.AlignCenter)
        name.setFixedHeight(24)
        name.setWordWrap(True)
        v.addWidget(name)

        # --- D&D 有効化
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose, False
        )  # 破棄はプール側が管理

    # --- Drag ---
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_ASSET_PATH, QByteArray(str(self.asset.path).encode()))
        drag.setMimeData(mime)
        drag.setHotSpot(e.position().toPoint())
        drag.setPixmap(self.grab())  # サムネイルをドラッグ画像に
        drag.exec(Qt.DropAction.CopyAction)


class MediaPoolWidget(QWidget):
    """
    +--------- QScrollArea -------------------------------------------+
    | MediaItem MediaItem MediaItem                                   |
    | MediaItem MediaItem MediaItem  ← QGridLayout (Flow 的な配置)    |
    +-----------------------------------------------------------------+
    """

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("MediaPoolWidget")
        self._project = project
        self._thumb_size = 96
        self._col_count = 3

        root = QVBoxLayout(self)
        add_btn = QPushButton("+ メディアを追加...")
        add_btn.clicked.connect(self._choose_file)
        root.addWidget(add_btn)

        # スクロール領域
        self._area = QScrollArea(widgetResizable=True)
        root.addWidget(self._area)

        self._content = QWidget()
        self._grid = QGridLayout(self._content)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setSpacing(8)
        self._area.setWidget(self._content)

        self._assets: list[MediaAsset] = []

    # ---
    def set_project(self, project: Project) -> None:
        self._project = project
        self._clear_assets()

    # --- Media import ---
    def _choose_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "メディアを選択", "", "Media Files (*.mp4 *.mov *.png *.jpg *.wav)"
        )
        for p in paths:
            self._import_media(Path(p))

    def _import_media(self, path: Path) -> None:
        # メディアタイプの判定
        mtype = (
            MediaType.IMAGE
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
            else MediaType.VIDEO
        )

        # メディア情報を取得
        try:
            media_info = probe(path)
            duration_ms = media_info.get("duration_ms", 0)
        except Exception:
            duration_ms = 10_000  # probe 失敗時はデフォルト10秒

        asset = MediaAsset(path, mtype, duration_ms=duration_ms)
        self._assets.append(asset)
        self._add_widget(asset)
        # Project 側でリスト管理したい場合はここで登録する

    # --- Grid helpers ---
    def _add_widget(self, asset: MediaAsset) -> None:
        idx = len(self._assets) - 1
        row, col = divmod(idx, self._col_count)
        w = MediaItemWidget(asset, self._thumb_size)
        self._grid.addWidget(w, row, col)

    def _clear_assets(self) -> None:
        while self._grid.count():
            self._grid.takeAt(0).widget().deleteLater()
        self._assets.clear()
