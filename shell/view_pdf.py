"""PDF 탭: 선택 이미지들을 한 PDF로 합치기."""
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import pdftool
import widgets as W

INNER = 360


class PdfView(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        p = pal
        tk.Label(self, text="%d개 이미지를 한 PDF로" % len(files), bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        lst = tk.Frame(self, bg=p["card"]); lst.pack(fill="x", pady=(8, 8))
        for f in files[:8]:
            tk.Label(lst, text="• " + W.elide(os.path.basename(f)), bg=p["card"], fg=p["sub"],
                     font=("Segoe UI", 9), anchor="w").pack(anchor="w")
        if len(files) > 8:
            tk.Label(lst, text="… 외 %d개" % (len(files) - 8), bg=p["card"], fg=p["sub"],
                     font=("Segoe UI", 9)).pack(anchor="w")
        r = tk.Frame(self, bg=p["card"]); r.pack(fill="x", pady=(4, 10))
        tk.Label(r, text="페이지", bg=p["card"], fg=p["sub"], font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.fit = W.Segmented(r, [("이미지 크기", "image"), ("A4 맞춤", "a4")], "image", p, w=INNER - 60)
        self.fit.pack(side="left")
        W.RoundButton(self, "PDF 만들기", self._make, p, "primary", w=INNER, h=40).pack()

    def _make(self):
        if not self.files:
            messagebox.showerror("이미지 다이어트", "이미지가 없습니다.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                           filetypes=[("PDF", "*.pdf")], initialfile="images.pdf")
        if not out:
            return
        try:
            saved = pdftool.images_to_pdf(self.files, out, fit=self.fit.value)
            messagebox.showinfo("이미지 다이어트", "저장됨: %s" % saved)
        except Exception as e:
            messagebox.showerror("이미지 다이어트", str(e))
