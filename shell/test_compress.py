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
