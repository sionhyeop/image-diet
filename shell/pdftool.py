"""이미지 여러 장 -> 한 PDF (tkinter 미의존)."""
import os
from PIL import Image

A4 = (595, 842)  # 72dpi 포인트


def _load_rgb(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def _fit_a4(im):
    page = Image.new("RGB", A4, (255, 255, 255))
    scale = min(A4[0] / im.width, A4[1] / im.height)
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    resized = im.resize((w, h), Image.LANCZOS)
    page.paste(resized, ((A4[0] - w) // 2, (A4[1] - h) // 2))
    return page


def page_preview(path, fit, box):
    im = _load_rgb(path)
    page = _fit_a4(im) if fit == "a4" else im
    thumb = page.copy()
    thumb.thumbnail(box, Image.LANCZOS)
    return thumb


def images_to_pdf(paths, out_path, fit="image"):
    if not paths:
        raise ValueError("이미지가 없습니다.")
    pages = []
    for p in paths:
        im = _load_rgb(p)
        pages.append(_fit_a4(im) if fit == "a4" else im)
    root, _ = os.path.splitext(out_path)
    final = root + ".pdf"
    pages[0].save(final, "PDF", save_all=True, append_images=pages[1:])
    return final
