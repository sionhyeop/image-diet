"""이미지 다이어트 압축 엔진 (UI 없음). Pillow 기반 순수 함수 모음."""
import os

EXT_FOR_FORMAT = {"webp": ".webp", "jpeg": ".jpg", "png": ".png"}


def resolve_format(src_path: str, out_format: str) -> str:
    fmt = (out_format or "auto").lower()
    if fmt == "auto":
        return "webp"
    return fmt


def numbered_output_path(src_path: str, out_ext: str) -> str:
    folder = os.path.dirname(os.path.abspath(src_path))
    stem = os.path.splitext(os.path.basename(src_path))[0]
    n = 1
    while True:
        candidate = os.path.join(folder, f"{stem}{n}{out_ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1
