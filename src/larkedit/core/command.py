from __future__ import annotations

import abc
from collections import deque
from typing import Deque, List, Optional

__all__ = ["Command", "MacroCommand", "UndoStack"]


class Command(abc.ABC):
    """
    すべての編集操作は Command に落とし込む

    execute() が成功したら True を返す
    undo()/redo() の返り値は省略 (例外は上位で捕捉)
    """

    #: ユーザー向けの説明 (メニューや履歴に)
    description: str = "Unnamed Command"

    def __init__(self, *, merge_id: Optional[str] = None) -> None:
        self._merge_id = merge_id  # 連続入力 (文字入力など) マージ用

    # --- Template Methods ---
    def execute(self) -> bool:
        """コマンドを実行してプロジェクトを変更する"""
        return self._execute()

    def undo(self) -> None:
        """実行内容を取り消す"""
        self._undo()

    def redo(self) -> None:
        """取り消した内容を再実行"""
        self._redo()

    # --- 必須実装部分 ---
    @abc.abstractmethod
    def _execute(self) -> bool: ...  # noqa: E704

    @abc.abstractmethod
    def _undo(self) -> None: ...  # noqa: E704

    def _redo(self) -> None:
        """多くの場合 redo は execute と同じで問題ない"""
        # デフォルト実装
        self._execute()

    # --- マージ判定 ---
    def can_merge_with(self, other: "Command") -> bool:
        """
        連続操作を 1 つにまとめたい時にオーバーライド。
        merge_id が一致すればマージ可能とする簡易実装。
        """
        return self._merge_id is not None and self._merge_id == other._merge_id

    def merge_with(self, other: "Command") -> bool:  # noqa: D401
        """other を self に取り込んだら True を返す（未使用なら False）"""
        return False  # デフォルトはマージしない


class MacroCommand(Command):
    """複数コマンドをまとめて 1 つに見せる"""

    description = "Macro Command"

    def __init__(self, commands: List[Command]) -> None:
        super().__init__()
        self._commands = commands

    def _execute(self) -> bool:
        for cmd in self._commands:
            if not cmd.execute():
                return False
        return True

    def _undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    def _redo(self) -> None:
        for cmd in self._commands:
            cmd.redo()


class UndoStack:
    """
    履歴の実装はシンプルなデック。

    - _history      … 実行済みコマンド
    - _undone       … Undo 済みで Redo 可能なコマンド
    """

    def __init__(self, max_depth: int | None = 1000) -> None:
        self._history: Deque[Command] = deque(maxlen=max_depth)
        self._undone: Deque[Command] = deque()

    # --- API ---
    def push(self, command: Command) -> bool:
        """
        コマンドを実行し、成功したら履歴に積む。
        必要ならマージ処理も行う。
        """
        if self._history and command.can_merge_with(self._history[-1]):
            merged = self._history[-1]
            if merged.merge_with(command):
                return True  # マージ完了 (新規エントリは不要)

        if command.execute():
            self._history.append(command)
            self._undone.clear()
            return True
        return False

    def undo(self) -> None:
        if not self._history:
            return
        cmd = self._history.pop()
        cmd.undo()
        self._undone.append(cmd)

    def redo(self) -> None:
        if not self._undone:
            return
        cmd = self._undone.pop()
        cmd.redo()
        self._history.append(cmd)

    # --- クエリ系 ---
    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    @property
    def can_redo(self) -> bool:
        return bool(self._undone)

    @property
    def undo_description(self) -> str | None:
        return self._history[-1].description if self._history else None

    @property
    def redo_description(self) -> str | None:
        return self._undone[-1].description if self._undone else None

    def clear(self) -> None:
        """履歴リセット (プロジェクト再読込時など)"""
        self._history.clear()
        self._undone.clear()
