from PIL import Image, ImageDraw
import svgtool


def _shape():
    im = Image.new("RGB", (120, 120), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 100, 100), fill=(220, 30, 30))
    d.rectangle((40, 40, 80, 80), fill=(20, 60, 200))
    return im


def test_opts_mapping():
    o = svgtool.opts_from_controls(colors=4, detail=5, simplify=2, noise=3, gap=1.0, smooth=True)
    assert o["colors"] == 4
    assert o["workRes"] == 640      # detail 5 -> RES[4]
    assert o["tol"] == 1.0          # simplify 2 -> TOL[2]
    assert o["minArea"] == 24       # noise 3 -> AREA[3]


def test_presets_exist():
    assert svgtool.PRESETS["logo"]["colors"] == 4
    assert svgtool.PRESETS["photo"]["detail"] == 5


def test_vectorize_produces_svg():
    o = svgtool.opts_from_controls(6, 3, 2, 2, 1.0, True)
    svg = svgtool.vectorize(_shape(), o)
    assert svg.lstrip().startswith("<svg")
    assert "<path" in svg
    assert svg.rstrip().endswith("</svg>")


def test_fewer_colors_is_valid():
    o = svgtool.opts_from_controls(2, 2, 2, 2, 1.0, True)
    svg = svgtool.vectorize(_shape(), o)
    assert "<svg" in svg and "</svg>" in svg


def test_rasterize_returns_image_within_box():
    o = svgtool.opts_from_controls(6, 3, 2, 2, 1.0, True)
    im = svgtool.rasterize(_shape(), o, box=(120, 100))
    from PIL import Image as _I
    assert isinstance(im, _I.Image)
    assert im.mode == "RGB"
    assert im.width <= 120 and im.height <= 100


def test_rasterize_not_blank():
    # 도형 이미지를 래스터화하면 배경 1색이 아니라 여러 색이 나와야 함
    o = svgtool.opts_from_controls(6, 3, 2, 2, 1.0, True)
    im = svgtool.rasterize(_shape(), o, box=(120, 100))
    colors = im.getcolors(maxcolors=100000)
    assert colors is not None and len(colors) >= 2


def _donut():
    # 흰 배경 + 파란 링(가운데 구멍은 배경색이어야 함)
    im = Image.new("RGB", (100, 100), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, 90, 90), fill=(20, 60, 200))
    d.ellipse((35, 35, 65, 65), fill=(255, 255, 255))
    return im


def _dark_ring():
    # 어두운 배경 + 밝은 링 (팔레트 순서가 중첩 순서와 반대인 케이스)
    im = Image.new("RGB", (100, 100), (20, 20, 30))
    d = ImageDraw.Draw(im)
    d.ellipse((15, 15, 85, 85), fill=(230, 230, 240))
    d.ellipse((40, 40, 60, 60), fill=(20, 20, 30))
    return im


def test_rasterize_keeps_hole():
    o = svgtool.opts_from_controls(4, 3, 2, 0, 1.0, True)
    im = svgtool.rasterize(_donut(), o)     # box 없이 원본 작업 해상도로
    cx, cy = im.width // 2, im.height // 2
    r, g, b = im.getpixel((cx, cy))
    # 가운데 구멍은 배경(흰색)에 가까워야 한다 — 링 색(파랑)으로 메워지면 실패
    assert r > 180 and g > 180 and b > 180, (r, g, b)


def test_rasterize_dark_ring_not_flat():
    o = svgtool.opts_from_controls(4, 3, 2, 0, 1.0, True)
    im = svgtool.rasterize(_dark_ring(), o)
    colors = im.getcolors(maxcolors=100000)
    # 링이 사라져 통짜 사각형이 되면 색이 1개 -> 실패
    assert colors is not None and len(colors) >= 2, colors
