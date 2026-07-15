import os
from PIL import Image
import compress


def test_resolve_format_auto_is_webp():
    assert compress.resolve_format("x.png", "auto") == "webp"


def test_resolve_format_passthrough():
    assert compress.resolve_format("x.png", "JPEG") == "jpeg"
    assert compress.resolve_format("x.png", "png") == "png"


def test_numbered_output_path_first(tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"x")
    out = compress.numbered_output_path(str(src), ".webp")
    assert out == str(tmp_path / "photo1.webp")


def test_numbered_output_path_avoids_collision(tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"x")
    (tmp_path / "photo1.webp").write_bytes(b"x")
    (tmp_path / "photo2.webp").write_bytes(b"x")
    out = compress.numbered_output_path(str(src), ".webp")
    assert out == str(tmp_path / "photo3.webp")


def _make_photo(path, size=(1600, 1200)):
    # 노이즈가 있어 쉽게 안 줄어드는 사진 유사 이미지
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        for x in range(0, size[0], 1):
            px[x, y] = ((x * 7) % 256, (y * 13) % 256, ((x + y) * 5) % 256)
    img.save(path, "PNG")


def test_compress_hits_target_webp(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src))
    before = src.read_bytes()
    res = compress.compress_image(str(src), target_kb=60, out_format="auto")
    assert res["ok"] is True
    assert res["out_path"] == str(tmp_path / "shot1.webp")
    assert os.path.exists(res["out_path"])
    assert res["size_kb"] <= 60
    # 원본 미변경
    assert src.read_bytes() == before


def test_compress_jpeg_format(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src), size=(800, 600))
    res = compress.compress_image(str(src), target_kb=40, out_format="jpeg")
    assert res["out_path"].endswith(".jpg")
    with Image.open(res["out_path"]) as im:
        assert im.format == "JPEG"


def test_compress_png_reduces_under_target(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src), size=(1200, 900))
    res = compress.compress_image(str(src), target_kb=80, out_format="png")
    assert res["ok"] is True
    assert res["size_kb"] <= 80
    assert res["out_path"].endswith(".png")


def test_compress_bad_file_returns_error(tmp_path):
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"not an image")
    res = compress.compress_image(str(bad), target_kb=50, out_format="auto")
    assert res["ok"] is False
    assert "error" in res
