from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from ..core.project import Project  # 編集モデル
from .editor import EditorPage
from .welcome import WelcomePage


class MainWindow(QMainWindow):
    """
    画面遷移を QStackedWidget で制御。
    起動時に Welcome -> プロジェクト決定後 Editor へ。
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LarkEdit")
        self.resize(1280, 720)

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        # --- ページ生成 ---
        self._welcome = WelcomePage(self)
        self._stack.addWidget(self._welcome)
        self._stack.setCurrentWidget(self._welcome)

        # EditorPage は遅延生成
        self._editor: EditorPage | None = None

        # --- シグナル接続 ---
        self._welcome.new_project_requested.connect(self._create_new_project)
        self._welcome.open_project_requested.connect(self._open_project_from_path)

    # ---
    # WelcomePage -> EditorPage 遷移ハンドラ
    # ---
    def _create_new_project(self) -> None:
        project = Project()
        self._open_editor(project)

    def _open_project_from_path(self, path: Path) -> None:
        # TODO: Project.load(path)
        project = Project(name=path.stem)
        self._open_editor(project)

    def _open_editor(self, project: Project) -> None:
        if self._editor is None:
            self._editor = EditorPage(project, self)
            self._stack.addWidget(self._editor)
        else:
            self._editor.set_project(project)
        self._stack.setCurrentWidget(self._editor)

    # --- アプリ終了用ラッパ (CLI から呼び出し) ---
    @staticmethod
    def run() -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        sys.exit(app.exec())
