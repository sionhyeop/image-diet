"""SVG 탭: 파라미터 조절 후 이미지->SVG 변환·저장."""
import os
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import compress
import svgtool
import widgets as W

INNER = 360
SLIDERS = [
    ("색상 수", "colors", 2, 16, 6),
    ("추적 정밀도", "detail", 1, 5, 3),
    ("외곽선 단순화", "simplify", 0, 4, 2),
    ("잡티 제거", "noise", 0, 4, 2),
    ("빈틈 메우기", "gap", 0, 4, 2),
]


class SvgView(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        self._last = None
        p = pal
        self.vars = {}
        pr = tk.Frame(self, bg=p["card"]); pr.pack(fill="x", pady=(0, 8))
        tk.Label(pr, text="프리셋", bg=p["card"], fg=p["sub"], font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        for key, label in (("logo", "로고"), ("illust", "일러스트"), ("photo", "사진")):
            W.RoundButton(pr, label, (lambda k=key: self._preset(k)), p, "ghost", w=74, h=30).pack(side="left", padx=3)
        grid = tk.Frame(self, bg=p["card"]); grid.pack(fill="x")
        for i, (label, key, lo, hi, dv) in enumerate(SLIDERS):
            tk.Label(grid, text=label, bg=p["card"], fg=p["sub"], font=("Segoe UI", 9),
                     anchor="w").grid(row=i, column=0, sticky="w", pady=3)
            v = tk.DoubleVar(value=dv) if key == "gap" else tk.IntVar(value=dv)
            self.vars[key] = v
            res = "0.5" if key == "gap" else 1
            tk.Scale(grid, from_=lo, to=hi, resolution=res, orient="horizontal",
                     variable=v, length=INNER - 96, bg=p["card"], fg=p["ink"],
                     troughcolor=p["field"], highlightthickness=0, bd=0).grid(row=i, column=1, sticky="w")
        self.smooth = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="곡선 스무딩", variable=self.smooth, bg=p["card"], fg=p["sub"],
                       selectcolor=p["field"], activebackground=p["card"]).pack(anchor="w", pady=(4, 8))
        b = tk.Frame(self, bg=p["card"]); b.pack(fill="x")
        W.RoundButton(b, "SVG 변환", self._convert, p, "primary", w=INNER - 110, h=40).pack(side="left")
        self.openbtn = W.RoundButton(b, "결과 열기", self._open, p, "ghost", w=102, h=40)
        self.openbtn.pack(side="right")

        self.preview = W.Preview(self, self.pal, (260, 220))
        self.preview.pack(pady=(10, 0))
        self._pending = None
        self._gen = 0
        for v in self.vars.values():
            v.trace_add("write", lambda *a: self._schedule())
        self.smooth.trace_add("write", lambda *a: self._schedule())
        self._schedule()  # 첫 렌더

    def _schedule(self):
        if self._pending is not None:
            try:
                self.after_cancel(self._pending)
            except Exception:
                pass
        self._pending = self.after(400, self._render_preview)

    def _render_preview(self):
        self._pending = None
        if not self.files:
            return
        opts = svgtool.opts_from_controls(
            self.vars["colors"].get(), self.vars["detail"].get(),
            self.vars["simplify"].get(), self.vars["noise"].get(),
            self.vars["gap"].get(), self.smooth.get())
        self._gen += 1
        gen = self._gen
        src = self.files[0]
        threading.Thread(target=self._render_work, args=(src, opts, gen), daemon=True).start()

    def _render_work(self, src, opts, gen):
        try:
            img = Image.open(src).convert("RGB")
            preview_img = svgtool.rasterize(img, opts, box=(260, 220))
        except Exception:
            return
        self._post(lambda: self._apply_preview(preview_img, gen))

    def _apply_preview(self, img, gen):
        if gen == self._gen:
            self.preview.set(img)
            self.recenter()

    def _post(self, fn):
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except (tk.TclError, RuntimeError):
            pass

    def _preset(self, key):
        pr = svgtool.PRESETS[key]
        for k in ("colors", "detail", "simplify", "noise"):
            self.vars[k].set(pr[k])
        self.smooth.set(pr["smooth"])

    def _convert(self):
        if not self.files:
            return
        opts = svgtool.opts_from_controls(
            self.vars["colors"].get(), self.vars["detail"].get(),
            self.vars["simplify"].get(), self.vars["noise"].get(),
            self.vars["gap"].get(), self.smooth.get())
        src = self.files[0]
        threading.Thread(target=self._work, args=(src, opts), daemon=True).start()

    def _work(self, src, opts):
        try:
            img = Image.open(src).convert("RGB")
            svg = svgtool.vectorize(img, opts)
            out = compress.numbered_output_path(src, ".svg")
            with open(out, "w", encoding="utf-8") as f:
                f.write(svg)
            self._last = out
            self._post(lambda: messagebox.showinfo("이미지 다이어트", "저장됨: %s" % out))
        except Exception as e:
            self._post(lambda: messagebox.showerror("이미지 다이어트", str(e)))

    def _open(self):
        if self._last and os.path.exists(self._last):
            try:
                os.startfile(self._last)  # noqa: WPS (Windows 전용)
            except Exception as e:
                messagebox.showerror("이미지 다이어트", "열기 실패: %s" % e)
