"""이미지 다이어트 압축 엔진 (UI 없음). Pillow 기반 순수 함수 모음."""
import os
import io
from PIL import Image, ImageOps

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


_MIN_Q, _MAX_Q, _SEARCH_STEPS = 30, 95, 6
_RES_STEP = 0.78          # 목표 미달 시 해상도 축소 비율
_MAX_RES_RETRIES = 6


def encode_to_bytes(img, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, "PNG", optimize=True)
    elif fmt == "jpeg":
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            rgb = bg
        else:
            rgb = img.convert("RGB")
        rgb.save(buf, "JPEG", quality=quality, optimize=True)
    else:  # webp
        img.save(buf, "WEBP", quality=quality, method=6)
    return buf.getvalue()


def step_down_resize(img, scale: float):
    if scale >= 1.0:
        return img
    tw = max(1, round(img.width * scale))
    th = max(1, round(img.height * scale))
    cur = img
    # 목표의 2배 이하가 될 때까지 절반씩
    while cur.width > tw * 2 and cur.height > th * 2:
        cur = cur.resize((cur.width // 2, cur.height // 2), Image.LANCZOS)
    if (cur.width, cur.height) != (tw, th):
        cur = cur.resize((tw, th), Image.LANCZOS)
    return cur


def _best_under_target(img, fmt: str, target_bytes: int) -> bytes:
    """품질 이진탐색으로 target_bytes 이하 중 최고 품질 바이트를 찾음.
    png는 품질 개념이 없어 그대로 인코딩."""
    if fmt == "png":
        return encode_to_bytes(img, fmt, 0)
    lo, hi = _MIN_Q, _MAX_Q
    best = None
    for _ in range(_SEARCH_STEPS):
        mid = (lo + hi) // 2
        data = encode_to_bytes(img, fmt, mid)
        if len(data) <= target_bytes:
            best = data
            lo = mid + 1
        else:
            hi = mid - 1
        if lo > hi:
            break
    if best is not None:
        return best
    # 최저 품질도 초과 → 최저 품질 바이트 반환(해상도 축소는 상위에서)
    return encode_to_bytes(img, fmt, _MIN_Q)


def compress_image(src_path: str, target_kb, out_format: str) -> dict:
    try:
        with Image.open(src_path) as opened:
            img = ImageOps.exif_transpose(opened)
            fmt = resolve_format(src_path, out_format)

            if target_kb is None:
                data = encode_to_bytes(img, fmt, 82)
            else:
                target_bytes = int(target_kb) * 1024
                work = img
                data = _best_under_target(work, fmt, target_bytes)
                retries = 0
                while len(data) > target_bytes and retries < _MAX_RES_RETRIES:
                    work = step_down_resize(work, _RES_STEP)
                    data = _best_under_target(work, fmt, target_bytes)
                    retries += 1

            out_ext = EXT_FOR_FORMAT[fmt]
            out_path = numbered_output_path(src_path, out_ext)
            with open(out_path, "wb") as f:
                f.write(data)
            return {"ok": True, "out_path": out_path,
                    "size_kb": max(1, round(len(data) / 1024))}
    except Exception as e:  # 손상 파일 등은 건너뜀
        return {"ok": False, "src_path": src_path, "error": str(e)}
