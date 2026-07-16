import base64
import os
from PIL import Image
import b64tool


def _png(path):
    Image.new("RGB", (8, 8), (200, 30, 30)).save(path, "PNG")


def test_to_data_uri_png(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    uri = b64tool.to_data_uri(str(p))
    assert uri.startswith("data:image/png;base64,")
    head, b64 = uri.split(",", 1)
    assert base64.b64decode(b64)[:8] == b"\x89PNG\r\n\x1a\n"


def test_variants_shapes(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    v = b64tool.variants(str(p))
    assert v["datauri"].startswith("data:image/png;base64,")
    assert v["imgtag"].startswith("<img src=\"data:image/png;base64,") and v["imgtag"].endswith("\">")
    assert v["css"].startswith("background-image:url(\"data:image/png;base64,") and v["css"].endswith("\")")


def test_decode_data_uri_roundtrip(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    uri = b64tool.to_data_uri(str(p))
    out = b64tool.decode_to_file(uri, str(tmp_path / "out"))
    assert out.endswith(".png")
    with Image.open(out) as im:
        assert im.size == (8, 8)


def test_decode_raw_base64_detects_png(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    raw = base64.b64encode(open(p, "rb").read()).decode()
    out = b64tool.decode_to_file(raw, str(tmp_path / "out"))
    assert out.endswith(".png")


def test_decode_bad_input_raises(tmp_path):
    try:
        b64tool.decode_to_file("not base64 @@@", str(tmp_path / "out"))
        assert False, "expected error"
    except ValueError:
        pass
