from PIL import Image
import pdftool

# Patch PIL to support PDF reading via PyMuPDF
try:
    import fitz
    _original_image_open = Image.open
    def _patched_open(fp, *args, **kwargs):
        if isinstance(fp, str) and fp.endswith('.pdf'):
            doc = fitz.open(fp)
            # Get page dimensions without rendering
            rect = doc[0].rect
            pil_img = Image.new("RGB", (int(rect.width), int(rect.height)), (255, 255, 255))
            doc.close()
            return pil_img
        return _original_image_open(fp, *args, **kwargs)
    Image.open = _patched_open
except ImportError:
    pass


def _img(path, size, color):
    Image.new("RGB", size, color).save(path)


def test_combine_pages(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (100, 80), (255, 0, 0))
    b = tmp_path / "b.png"; _img(str(b), (60, 120), (0, 128, 0))
    out = pdftool.images_to_pdf([str(a), str(b)], str(tmp_path / "doc.pdf"))
    assert out.endswith(".pdf")
    with open(out, "rb") as f:
        head = f.read(5)
    assert head == b"%PDF-"


def test_a4_fit_runs(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (2000, 100), (10, 10, 200))
    out = pdftool.images_to_pdf([str(a)], str(tmp_path / "d.pdf"), fit="a4")
    with Image.open(out) as im:
        assert im.size == (595, 842)


def test_empty_raises(tmp_path):
    try:
        pdftool.images_to_pdf([], str(tmp_path / "x.pdf"))
        assert False
    except ValueError:
        pass
