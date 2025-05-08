import threading
import time
from pathlib import Path

import numpy as np

from larkedit.encoding.ffmpeg_binding import encoder as ffm  # type: ignore
from larkedit.utils import media

# --- encoder example ---

OUT_DIR = Path("example_output")
OUT_DIR.mkdir(exist_ok=True)
VIDEO_FILE = OUT_DIR / "out_full.mp4"

WIDTH, HEIGHT = 640, 360
FPS = 30
DURATION_SEC = 5
FRAME_COUNT = FPS * DURATION_SEC

SAMPLE_RATE = 48_000
CHANNELS = 2
AUDIO_CHUNK = 2048  # サンプル/チャンク

enc = ffm.MediaEncoder(
    filename=str(VIDEO_FILE),
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
    sample_rate=SAMPLE_RATE,
    channels=CHANNELS,
)
enc.start()
print("Encoder started")

comp = ffm.Compositor(WIDTH, HEIGHT)


def np_to_vframe(arr: np.ndarray, pts_ms: int) -> ffm.VideoFrame:  # type: ignore
    """numpy → VideoFrame 変換ヘルパ"""
    return ffm.VideoFrame(WIDTH, HEIGHT, pts_ms, arr.tobytes())


def audio_producer() -> None:
    """440 Hz 正弦波を 2048 サンプルずつ送信"""
    total_samples = SAMPLE_RATE * DURATION_SEC
    t = 0
    freq = 440.0
    # 時間計測で PTS を算出
    while t < total_samples:
        length = min(AUDIO_CHUNK, total_samples - t)
        ts = np.arange(length, dtype=np.float32) + t
        chunk = np.sin(2 * np.pi * freq * ts / SAMPLE_RATE).astype(np.float32)
        if CHANNELS == 2:
            chunk = np.repeat(chunk[:, None], 2, axis=1).flatten()
        pts_ms = int(t * 1000 / SAMPLE_RATE)
        enc.submit_audio(chunk, pts_ms)
        t += length
    print("Audio thread finished")


audio_thread = threading.Thread(target=audio_producer, daemon=True)
audio_thread.start()
print("Audio thread started")

for i in range(FRAME_COUNT):
    pts_ms = int(i * 1000 / FPS)

    bg = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    bg[..., 2] = 255  # B
    bg[..., 3] = 255  # A

    ov = np.zeros_like(bg)
    rect_w, rect_h = 80, 60
    x = int((WIDTH - rect_w) * i / (FRAME_COUNT - 1))
    y = (HEIGHT - rect_h) // 2
    ov[y : y + rect_h, x : x + rect_w, 0] = 255  # R
    ov[y : y + rect_h, x : x + rect_w, 3] = 255  # A

    # Compositor でレイヤブレンド
    vf_bg = np_to_vframe(bg, pts_ms)
    vf_ov = np_to_vframe(ov, pts_ms)
    composed = comp.compose([vf_bg, vf_ov])

    # Encoder へ送信
    rgba = np.frombuffer(bytes(composed.rgba), dtype=np.uint8).reshape(
        (HEIGHT, WIDTH, 4)
    )
    enc.submit_video(rgba, pts_ms)

    # 擬似リアルタイム送信 (早すぎるとキュー飽和を検証しにくいので 10 ms sleep)
    time.sleep(0.01)

print("Video thread finished")

audio_thread.join()
print("Audio thread joined")
enc.finish()
print("done :", VIDEO_FILE)


# --- probe example ---

print("probe example")
data = media.probe(VIDEO_FILE)
for k, v in data.items():
    print(f"{k}: {v}")
print("probe done")

# --- thumbnail example ---

print("thumbnail example")
from PySide6.QtGui import QGuiApplication  # noqa

app = QGuiApplication([])
img = media.thumbnail_qpixmap(VIDEO_FILE, 1000, 128)
img.save(str(OUT_DIR / "thumb.png"))
print("thumbnail done")
app = None  # cleanup
