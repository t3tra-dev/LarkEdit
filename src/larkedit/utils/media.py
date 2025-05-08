from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from ..encoding.ffmpeg_binding import probe as _probe_mod  # type: ignore


class VideoInfo(TypedDict, total=False):
    width: int
    height: int
    fps: float


class AudioInfo(TypedDict, total=False):
    sample_rate: int
    channels: int


class MediaInfo(TypedDict, total=False):
    duration_ms: int
    video: VideoInfo
    audio: AudioInfo


def probe(path: str | Path) -> MediaInfo:
    """FFmpeg でメディア情報を取得。辞書で返す。"""
    return _probe_mod.probe(str(path))  # type: ignore[return-value]


def thumbnail_qpixmap(path: str | Path, ms: int = 0, size: int = 96) -> QPixmap:
    """
    指定時刻 ms のフレームを取得し、正方サムネイルにして QPixmap 返却。
    失敗時は単色プレースホルダ。
    """
    try:
        w, h, rgba_bytes = _probe_mod.extract_rgba_frame(str(path), ms, size, size)
        arr = np.frombuffer(rgba_bytes, dtype=np.uint8).reshape((h, w, 4))
        img = QImage(arr.data, w, h, QImage.Format.Format_RGBA8888)
        pm = QPixmap.fromImage(img)
        if max(w, h) > size:  # 念のため
            pm = pm.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pm
    except Exception:  # noqa: BLE001
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.gray)
        return pm
