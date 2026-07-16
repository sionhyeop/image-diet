from PIL import Image
import pdftool


def _img(path, size, color):
    Image.new("RGB", size, color).save(path)


def test_combine_pages(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (100, 80), (255, 0, 0))
    b = tmp_path / "b.png"; _img(str(b), (60, 120), (0, 128, 0))
    out = pdftool.images_to_pdf([str(a), str(b)], str(tmp_path / "doc.pdf"))
    assert out.endswith(".pdf")
    with open(out, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_a4_fit_produces_a4_page():
    # Pillow can't READ PDFs, so verify the A4 fit on the helper directly.
    page = pdftool._fit_a4(Image.new("RGB", (2000, 100), (10, 10, 200)))
    assert page.size == (595, 842)


def test_a4_pdf_is_written(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (2000, 100), (10, 10, 200))
    out = pdftool.images_to_pdf([str(a)], str(tmp_path / "d.pdf"), fit="a4")
    assert out.endswith(".pdf")
    with open(out, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_empty_raises(tmp_path):
    try:
        pdftool.images_to_pdf([], str(tmp_path / "x.pdf"))
        assert False
    except ValueError:
        pass


def test_page_preview_image_fit(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (400, 200), (200, 30, 30))
    im = pdftool.page_preview(str(a), "image", (100, 100))
    from PIL import Image as _I
    assert isinstance(im, _I.Image)
    assert im.width <= 100 and im.height <= 100
    # 원본 2:1 비율 유지 -> 100x50 근처
    assert im.width > im.height


def test_page_preview_a4_fit(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (400, 200), (10, 10, 200))
    im = pdftool.page_preview(str(a), "a4", (200, 300))
    assert im.width <= 200 and im.height <= 300
    # A4 세로 비율(595:842) -> 세로가 더 김
    assert im.height > im.width
