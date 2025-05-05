from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from ...core.project import Project


class PreviewWidget(QLabel):
    """
    タイムラインの現在フレームを表示。
    今はプレースホルダとして真っ黒の QPixmap。
    """

    def __init__(self, project: Project, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PreviewWidget")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.set_project(project)

    # ---
    def set_project(self, project: Project) -> None:
        self._project = project
        self._update_placeholder()

    def _update_placeholder(self) -> None:
        pm = QPixmap(640, 360)
        pm.fill(QColor("black"))
        self.setPixmap(pm)
