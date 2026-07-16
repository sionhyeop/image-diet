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
