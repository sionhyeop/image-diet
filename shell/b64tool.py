"""Base64 인코딩/디코딩 (tkinter 미의존)."""
import base64
import binascii
import os

from PIL import Image

import compress

_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"BM", "bmp", "image/bmp"),
    (b"GIF8", "gif", "image/gif"),
]


def _sniff(data: bytes):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    for sig, ext, mime in _MAGIC:
        if data.startswith(sig):
            return ext, mime
    return "png", "image/png"


def to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    _ext, mime = _sniff(data)
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))


def variants(path: str) -> dict:
    uri = to_data_uri(path)
    return {
        "datauri": uri,
        "imgtag": '<img src="%s">' % uri,
        "css": 'background-image:url("%s")' % uri,
    }


def decode_to_file(text: str, out_path: str) -> str:
    s = (text or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma < 0:
            raise ValueError("잘못된 Data URI 입니다.")
        s = s[comma + 1:]
    s = "".join(s.split())
    try:
        data = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Base64 문자열을 해석할 수 없습니다.")
    if not data:
        raise ValueError("빈 데이터입니다.")
    ext, _mime = _sniff(data)
    root, _ = os.path.splitext(out_path)
    final = root + "." + ext
    with open(final, "wb") as f:
        f.write(data)
    return final


def to_data_uri_compressed(path: str, max_side: int = 1920, quality: float = 0.8) -> dict:
    """웹앱의 '압축해서 변환'과 동일: 긴 변 max_side 로 축소 후 WebP 재인코딩 → Data URI."""
    orig_bytes = os.path.getsize(path)
    with Image.open(path) as opened:
        if opened.mode in ("RGBA", "LA") or "transparency" in opened.info:
            img = opened.convert("RGBA")
        elif opened.mode != "RGB":
            img = opened.convert("RGB")
        else:
            img = opened.copy()
        w, h = img.size
        scale = min(1.0, float(max_side) / max(w, h)) if max(w, h) else 1.0
        if scale < 1.0:
            img = compress.step_down_resize(img, scale)
        data = compress.encode_to_bytes(img, "webp", int(round(quality * 100)))
        ow, oh = img.size
    uri = "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
    return {
        "datauri": uri,
        "imgtag": '<img src="%s">' % uri,
        "css": 'background-image:url("%s")' % uri,
        "orig_bytes": orig_bytes,
        "comp_bytes": len(data),
        "w": ow,
        "h": oh,
    }
