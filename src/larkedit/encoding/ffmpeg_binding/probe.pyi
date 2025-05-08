from typing import Dict, Literal, Tuple, Union

def probe(file: str) -> Union[
    Dict[Literal["duration_ms"], int],
    Dict[Literal["video"], Dict[Literal["width", "height", "fps"], int | float]],
    Dict[Literal["audio"], Dict[Literal["sample_rate", "channels"], int]] | None,
]: ...
def extract_rgba_frame(
    file: str, ms: int = 0, max_w: int = 256, max_h: int = 256
) -> Tuple[int, int, bytes]: ...
