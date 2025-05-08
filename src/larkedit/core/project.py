from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Protocol, Union, runtime_checkable

__all__ = ["Project", "MediaAsset", "Clip", "Track", "Timeline"]

# --- 基本データ型 ---


class MediaType:
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


@dataclass(slots=True)
class MediaAsset:
    """インポートしたメディアファイル"""

    path: Path
    media_type: str  # see MediaType.*
    duration_ms: int


@dataclass(slots=True)
class Clip:
    """タイムライン上に配置される 1 つのメディア片"""

    asset: MediaAsset
    in_point_ms: int  # asset 先頭からのオフセット
    duration_ms: int
    start_ms: int  # タイムライン上の開始位置

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


@dataclass(slots=True)
class Track:
    """映像／音声トラック"""

    index: int
    name: str
    clips: List[Clip] = field(default_factory=list)

    # --- インターフェース ---
    def add_clip(self, clip: Clip) -> None:
        """clip をタイムライン位置順に挿入 (単純 O(n) で十分)"""
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_ms)

    def remove_clip(self, clip: Clip) -> None:
        self.clips.remove(clip)

    def find_clip_at(self, position_ms: int) -> Clip | None:
        """position_ms が含まれる clip を返す (無ければ None)"""
        for c in self.clips:
            if c.start_ms <= position_ms < c.end_ms:
                return c
        return None


@dataclass(slots=True)
class Timeline:
    """複数 Track を束ねるコンテナ"""

    tracks: List[Track] = field(default_factory=list)

    def add_track(self, track: Track) -> None:
        self.tracks.append(track)
        self.tracks.sort(key=lambda t: t.index)

    def remove_track(self, track: Track) -> None:
        self.tracks.remove(track)

    def track(self, index: int) -> Track:
        return next(t for t in self.tracks if t.index == index)


# --- プロジェクト本体 ---


@runtime_checkable
class ProjectObserver(Protocol):
    """GUI などが実装して Project 変化を受け取る"""

    def project_changed(self, *, description: str) -> None: ...  # noqa: E704


@dataclass
class Project:
    """Project はタイムラインと各種設定のルート"""

    name: str = "Untitled"
    fps: int = 30
    width: int = 1920
    height: int = 1080
    timeline: Timeline = field(default_factory=Timeline)
    undo_stack: Union["UndoStack", None] = None  # lazy import

    _observers: List[ProjectObserver] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """初期化後に実行される。デフォルトのトラックを作成する"""
        # デフォルトでビデオトラックを追加
        if not self.timeline.tracks:
            video_track = Track(index=0, name="video")
            # audio_track = Track(index=1, name="audio")
            self.timeline.add_track(video_track)
            # self.timeline.add_track(audio_track)

    # --- 公開 API ---
    def attach_observer(self, obs: ProjectObserver) -> None:
        if obs not in self._observers:
            self._observers.append(obs)

    def detach_observer(self, obs: ProjectObserver) -> None:
        self._observers.remove(obs)

    # --- タイムライン操作をユーティリティとしてラップ ---
    def add_clip(
        self,
        track_index: int,
        asset: MediaAsset,
        start_ms: int,
        in_point_ms: int = 0,
        duration_ms: int | None = None,
    ) -> None:
        """
        UndoStack を通さずに内部呼び出し可能 (コマンド側から呼ばれる想定)。
        GUI から直接呼ぶ場合は必ず Command を介して push すること。
        """
        track = self.timeline.track(track_index)
        clip = Clip(
            asset=asset,
            in_point_ms=in_point_ms,
            duration_ms=duration_ms or asset.duration_ms,
            start_ms=start_ms,
        )
        track.add_clip(clip)

        self._notify(f"Add clip to track {track_index}")

    def remove_clip(self, track_index: int, clip: Clip) -> None:
        track = self.timeline.track(track_index)
        track.remove_clip(clip)
        self._notify(f"Remove clip from track {track_index}")

    # --- 内部 util ---
    def _notify(self, description: str) -> None:
        for obs in self._observers:
            obs.project_changed(description=description)


# --- Ex: 基本コマンド ---

# 遅延インポート (循環回避)
from .command import Command  # noqa: E402
from .command import UndoStack  # noqa: E402


class AddClipCommand(Command):
    """Project に Clip を1つ追加する"""

    description = "Add Clip"

    def __init__(
        self,
        project: Project,
        *,
        track_index: int,
        asset: MediaAsset,
        start_ms: int,
        in_point_ms: int = 0,
        duration_ms: int | None = None,
    ):
        super().__init__()
        self._project = project
        self._track_index = track_index
        self._asset = asset
        self._start_ms = start_ms
        self._in_point_ms = in_point_ms
        self._duration_ms = duration_ms
        self._clip: Clip | None = None

    # --- Command impl ---
    def _execute(self) -> bool:
        self._project.add_clip(
            self._track_index,
            self._asset,
            self._start_ms,
            self._in_point_ms,
            self._duration_ms,
        )
        # 直近に追加された Clip を記憶 (簡便策)
        track = self._project.timeline.track(self._track_index)
        self._clip = track.clips[-1]
        return True

    def _undo(self) -> None:
        if self._clip:
            self._project.remove_clip(self._track_index, self._clip)
            self._clip = None
