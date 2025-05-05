from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QDoubleSpinBox,
    QLabel,
)

from ...core.project import Clip, Project


class PropertyEditorWidget(QWidget):
    """
    選択された Clip のプロパティ表示・編集。
    今は duration_ms と in_point_ms だけサポート。
    """

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PropertyEditorWidget")
        self._project = project

        self._form = QFormLayout(self)
        self._in_spin = QDoubleSpinBox(decimals=0, suffix=" ms", maximum=1e6)
        self._dur_spin = QDoubleSpinBox(decimals=0, suffix=" ms", maximum=1e6)

        for w in (self._in_spin, self._dur_spin):
            w.valueChanged.connect(self._apply_changes)

        self._form.addRow(QLabel("<b>クリッププロパティ</b>"))
        self._form.addRow("In Point", self._in_spin)
        self._form.addRow("Duration", self._dur_spin)
        self.setEnabled(False)

    # ---
    def set_project(self, project: Project) -> None:
        self._project = project
        self.clear_selection()

    def show_clip(self, clip: Clip) -> None:
        self._clip = clip
        self._in_spin.setValue(clip.in_point_ms)
        self._dur_spin.setValue(clip.duration_ms)
        self.setEnabled(True)

    def clear_selection(self) -> None:
        self._clip: Clip | None = None
        self.setEnabled(False)

    def _apply_changes(self) -> None:
        if not self._clip:
            return
        self._clip.in_point_ms = int(self._in_spin.value())
        self._clip.duration_ms = int(self._dur_spin.value())
