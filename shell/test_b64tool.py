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


def _big(path, size=(3000, 1500)):
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(0, size[1], 3):
        for x in range(0, size[0], 3):
            px[x, y] = ((x * 7) % 256, (y * 13) % 256, ((x + y) * 5) % 256)
    img.save(path, "PNG")


def test_compressed_caps_long_side_to_1920(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert max(r["w"], r["h"]) == 1920
    assert r["w"] == 1920 and r["h"] == 960          # 3000x1500 -> 2:1 유지
    assert r["datauri"].startswith("data:image/webp;base64,")


def test_compressed_is_smaller_than_raw(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    raw = b64tool.to_data_uri(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert len(r["datauri"]) < len(raw)               # 압축이 실제로 짧아야 함
    assert r["comp_bytes"] < r["orig_bytes"]


def test_compressed_small_image_not_upscaled(tmp_path):
    p = tmp_path / "small.png"
    Image.new("RGB", (100, 80), (10, 200, 120)).save(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert (r["w"], r["h"]) == (100, 80)              # 확대 금지


def test_compressed_quality_affects_size(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    lo = b64tool.to_data_uri_compressed(str(p), quality=0.4)
    hi = b64tool.to_data_uri_compressed(str(p), quality=0.95)
    assert lo["comp_bytes"] < hi["comp_bytes"]


def test_compressed_variants_shapes(tmp_path):
    p = tmp_path / "small.png"
    Image.new("RGB", (60, 40), (200, 30, 30)).save(str(p))
    r = b64tool.to_data_uri_compressed(str(p))
    assert r["imgtag"].startswith('<img src="data:image/webp;base64,') and r["imgtag"].endswith('">')
    assert r["css"].startswith('background-image:url("data:image/webp;base64,') and r["css"].endswith('")')
