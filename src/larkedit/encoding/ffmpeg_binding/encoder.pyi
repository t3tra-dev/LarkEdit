from __future__ import annotations

from typing import Sequence

import numpy as _np
from numpy.typing import NDArray

class VideoFrame:
    width: int
    height: int
    pts: int
    rgba: bytes

    def __init__(self, width: int, height: int, pts: int, rgba: bytes) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

class AudioSamples:
    pts: int  # milliseconds
    pcm: list[float]  # exposed as Python list for zero‑copy

    def __init__(self, pts: int, pcm: list[float]) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...

class Compositor:
    def __init__(self, canvas_width: int, canvas_height: int) -> None: ...
    def compose(self, layers: Sequence[VideoFrame]) -> VideoFrame: ...
    def __call__(self, layers: Sequence[VideoFrame]) -> VideoFrame: ...

class MediaEncoder:
    def __init__(
        self,
        filename: str,
        width: int,
        height: int,
        fps: int,
        sample_rate: int = 48_000,
        channels: int = 2,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        queue_cap: int = 32,
    ) -> None: ...
    def start(self) -> None: ...
    def submit_video(self, rgba: NDArray[_np.uint8], pts: int) -> None: ...
    def submit_audio(self, pcm: NDArray[_np.float32], pts: int) -> None: ...
    def finish(self) -> None: ...
    def __enter__(self) -> "MediaEncoder": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> bool: ...
    def __del__(self) -> None: ...
