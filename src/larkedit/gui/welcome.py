from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
)

RECENT_FILE = Path.home() / ".larkedit_recent"  # 単純なテキスト保存


class WelcomePage(QWidget):
    """
    最近開いたプロジェクトを列挙 + 新規作成ボタン。
    """

    new_project_requested = Signal()
    open_project_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("WelcomePage")

        vbox = QVBoxLayout(self)
        title = QLabel("<h2>最近使ったプロジェクト</h2>")
        vbox.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        vbox.addWidget(self._list)

        # footer: spacer + 新規ボタン
        footer = QHBoxLayout()
        footer.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding))
        new_btn = QPushButton("+ 新規プロジェクト")
        new_btn.clicked.connect(self.new_project_requested.emit)
        footer.addWidget(new_btn)
        vbox.addLayout(footer)

        self._populate()

    # ---
    def _populate(self) -> None:
        self._list.clear()
        if not RECENT_FILE.exists():
            return
        for line in RECENT_FILE.read_text().splitlines():
            p = Path(line)
            if p.exists():
                item = QListWidgetItem(p.name)
                item.setData(Qt.ItemDataRole.UserRole, p)
                self._list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path: Path = item.data(Qt.ItemDataRole.UserRole)
        self.open_project_requested.emit(path)
