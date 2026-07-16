"""공용 Tkinter 위젯·팔레트."""
import tkinter as tk
from PIL import Image


# ───────────────────────── 팔레트 ─────────────────────────
def is_dark():
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return v == 0
    except Exception:
        return False


def palette(dark):
    if dark:
        return dict(card="#1a2429", ink="#e7eef0", sub="#8ba3ab", hair="#2a373d",
                    field="#212d33", field_line="#33434a", accent="#2dd4bf",
                    accent2="#5eead4", accent_soft="#12332f", on_accent="#06201d",
                    ok="#4ade80", ok_soft="#10331d", warn="#f87171", warn_soft="#3a1c1c")
    return dict(card="#ffffff", ink="#16272d", sub="#5d757d", hair="#dde5e8",
                field="#f3f7f8", field_line="#d3dee1", accent="#0d9488",
                accent2="#0f766e", accent_soft="#d6f0ec", on_accent="#ffffff",
                ok="#16a34a", ok_soft="#dcfce7", warn="#dc2626", warn_soft="#fee2e2")


def human(n):
    if n >= 1024 * 1024:
        return "%.1fMB" % (n / 1048576.0)
    if n >= 1024:
        return "%dKB" % round(n / 1024.0)
    return "%dB" % n


# ───────────────────────── Canvas 유틸 ─────────────────────────
def round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def chip(parent, text, fg, bg, cardbg):
    cv = tk.Canvas(parent, height=22, bg=cardbg, highlightthickness=0)
    t = cv.create_text(11, 12, text=text, fill=fg,
                       font=("Segoe UI", 9, "bold"), anchor="w")
    x1, _y1, x2, _y2 = cv.bbox(t)
    w = (x2 - x1) + 22
    cv.configure(width=w)
    rr = round_rect(cv, 1, 2, w - 1, 20, 9, fill=bg, outline="")
    cv.tag_lower(rr)
    return cv


def elide(name, keep=30):
    if len(name) <= keep:
        return name
    return name[:keep - 14] + "…" + name[-13:]


def make_thumb(img, box):
    im = img.copy()
    im.thumbnail(box, Image.LANCZOS)
    return im


# ───────────────────────── 위젯 ─────────────────────────
class RoundButton(tk.Canvas):
    def __init__(self, parent, text, command, pal, kind="primary", w=120, h=40):
        super().__init__(parent, width=w, height=h, bg=pal["card"],
                         highlightthickness=0, cursor="hand2")
        self.command = command
        if kind == "primary":
            self._fill, self._hover = pal["accent"], pal["accent2"]
            self._fg, outline = pal["on_accent"], ""
        else:
            self._fill, self._hover = pal["card"], pal["field"]
            self._fg, outline = pal["sub"], pal["field_line"]
        self._rect = round_rect(self, 1, 1, w - 1, h - 1, 10,
                                 fill=self._fill, outline=outline)
        self.create_text(w // 2, h // 2, text=text, fill=self._fg,
                         font=("Segoe UI", 11, "bold"))
        self.bind("<Enter>", lambda e: self.itemconfig(self._rect, fill=self._hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self._rect, fill=self._fill))
        self.bind("<Button-1>", lambda e: self.command())


class Segmented(tk.Canvas):
    def __init__(self, parent, options, value, pal, w=324, h=34):
        super().__init__(parent, width=w, height=h, bg=pal["card"],
                         highlightthickness=0, cursor="hand2")
        self.options, self.pal, self.value = options, pal, value
        self.w, self.h, self.n = w, h, len(options)
        round_rect(self, 1, 1, w - 1, h - 1, 9,
                    fill=pal["field"], outline=pal["field_line"])
        self._dyn = []
        self._draw()
        self.bind("<Button-1>", self._click)

    def _seg_bounds(self, i):
        pad = 3
        seg = (self.w - 2 * pad) / self.n
        return pad + seg * i, pad + seg * (i + 1)

    def _draw(self):
        for item in self._dyn:
            self.delete(item)
        self._dyn = []
        for i, (label, val) in enumerate(self.options):
            x1, x2 = self._seg_bounds(i)
            sel = (val == self.value)
            if sel:
                self._dyn.append(round_rect(self, x1, 4, x2, self.h - 4, 7,
                                             fill=self.pal["accent"], outline=""))
            self._dyn.append(self.create_text(
                (x1 + x2) / 2, self.h / 2, text=label,
                fill=(self.pal["on_accent"] if sel else self.pal["sub"]),
                font=("Segoe UI", 10, "bold")))

    def _click(self, e):
        pad = 3
        seg = (self.w - 2 * pad) / self.n
        i = max(0, min(self.n - 1, int((e.x - pad) // seg)))
        self.value = self.options[i][1]
        self._draw()


class Bar(tk.Canvas):
    def __init__(self, parent, pal, w=324, h=6):
        super().__init__(parent, width=w, height=h, bg=pal["card"],
                         highlightthickness=0)
        self.w, self.h, self.pal = w, h, pal
        round_rect(self, 0, 0, w, h, h // 2, fill=pal["field"], outline="")
        self._fill = None

    def set(self, frac):
        if self._fill:
            self.delete(self._fill)
        fw = max(self.h, int(self.w * max(0.0, min(1.0, frac))))
        self._fill = round_rect(self, 0, 0, fw, self.h, self.h // 2,
                                 fill=self.pal["accent"], outline="")


class Preview(tk.Label):
    def __init__(self, parent, pal, box):
        super().__init__(parent, bg=pal["field"], bd=0)
        self._pal, self._box = pal, box
        self._ph = None

    def set(self, pil_img):
        try:
            from PIL import ImageTk
            thumb = make_thumb(pil_img, self._box)
            self._ph = ImageTk.PhotoImage(thumb)
            self.configure(image=self._ph, text="")
        except Exception:
            self._ph = None
            self.configure(image="", text="(미리보기 불가)",
                           fg=self._pal["sub"], font=("Segoe UI", 9))
