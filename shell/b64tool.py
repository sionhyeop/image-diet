"""Base64 인코딩/디코딩 (tkinter 미의존)."""
import base64
import binascii
import os

_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"RIFF", "webp", "image/webp"),   # RIFF....WEBP
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
