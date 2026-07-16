"""Base64 탭: 이미지->Data URI (복사), Base64->이미지 (저장)."""
import tkinter as tk
from tkinter import messagebox, filedialog
import b64tool
import widgets as W

INNER = 360


class Base64View(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        p = pal
        # 인코딩
        tk.Label(self, text="이미지 → Base64", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.enc = tk.Text(self, height=4, width=46, bg=p["field"], fg=p["ink"],
                           bd=0, relief="flat", wrap="char", insertbackground=p["ink"])
        self.enc.pack(fill="x", pady=(6, 6))
        row = tk.Frame(self, bg=p["card"]); row.pack(fill="x")
        W.RoundButton(row, "Data URI", lambda: self._copy("datauri"), p, "ghost", w=104, h=34).pack(side="left")
        W.RoundButton(row, "<img>", lambda: self._copy("imgtag"), p, "ghost", w=96, h=34).pack(side="left", padx=6)
        W.RoundButton(row, "CSS", lambda: self._copy("css"), p, "ghost", w=88, h=34).pack(side="left")
        if self.files:
            try:
                self._variants = b64tool.variants(self.files[0])
                self.enc.insert("1.0", self._variants["datauri"])
            except Exception as e:
                self._variants = None
                self.enc.insert("1.0", "인코딩 실패: %s" % e)
        else:
            self._variants = None
        # 디코딩
        tk.Frame(self, bg=p["hair"], height=1, width=INNER).pack(fill="x", pady=12)
        tk.Label(self, text="Base64 → 이미지", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.dec = tk.Text(self, height=4, width=46, bg=p["field"], fg=p["ink"],
                           bd=0, relief="flat", wrap="char", insertbackground=p["ink"])
        self.dec.pack(fill="x", pady=(6, 6))
        W.RoundButton(self, "이미지로 저장", self._save, p, "primary", w=INNER, h=38).pack()

    def _copy(self, key):
        if not self._variants:
            return
        self.clipboard_clear()
        self.clipboard_append(self._variants[key])
        messagebox.showinfo("이미지 다이어트", "복사했습니다.")

    def _save(self):
        text = self.dec.get("1.0", "end")
        if not text.strip():
            messagebox.showerror("이미지 다이어트", "Base64 문자열을 붙여넣으세요.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".png",
                                           filetypes=[("이미지", "*.png *.jpg *.webp *.bmp *.gif")])
        if not out:
            return
        try:
            saved = b64tool.decode_to_file(text, out)
            messagebox.showinfo("이미지 다이어트", "저장됨: %s" % saved)
        except ValueError as e:
            messagebox.showerror("이미지 다이어트", str(e))
