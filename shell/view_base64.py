"""Base64 탭: 이미지->Data URI (복사), Base64->이미지 (저장)."""
import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import b64tool
import widgets as W

INNER = 360


def _chars(n):
    return "{:,}자".format(n)


class Base64View(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        self._seq = 0
        self._qpend = None
        self._variants = None
        p = pal
        # 인코딩
        tk.Label(self, text="이미지 → Base64", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.preview = W.Preview(self, self.pal, (200, 150))
        self.preview.pack(pady=(0, 6))
        if self.files:
            try:
                from PIL import Image
                self.preview.set(Image.open(self.files[0]).convert("RGB"))
            except Exception:
                pass
        self.enc = tk.Text(self, height=4, width=46, bg=p["field"], fg=p["ink"],
                           bd=0, relief="flat", wrap="char", insertbackground=p["ink"])
        self.enc.pack(fill="x", pady=(6, 6))
        row = tk.Frame(self, bg=p["card"]); row.pack(fill="x")
        W.RoundButton(row, "Data URI", lambda: self._copy("datauri"), p, "ghost", w=104, h=34).pack(side="left")
        W.RoundButton(row, "<img>", lambda: self._copy("imgtag"), p, "ghost", w=96, h=34).pack(side="left", padx=6)
        W.RoundButton(row, "CSS", lambda: self._copy("css"), p, "ghost", w=88, h=34).pack(side="left")

        # 압축해서 변환
        self.do_comp = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="압축해서 변환  (최대 1920px + WebP 재인코딩)",
                       variable=self.do_comp, bg=p["card"], fg=p["ink"],
                       selectcolor=p["field"], activebackground=p["card"],
                       font=("Segoe UI", 9), command=self._reencode).pack(anchor="w")

        # 압축 품질 (체크 시에만 표시)
        self.qframe = tk.Frame(self, bg=p["card"])
        self.q = tk.DoubleVar(value=0.8)
        self.qlabel = tk.Label(self.qframe, text="압축 품질 80%", bg=p["card"], fg=p["sub"],
                               font=("Segoe UI", 9))
        self.qlabel.pack(anchor="w")
        tk.Scale(self.qframe, from_=0.4, to=0.95, resolution=0.01, orient="horizontal",
                 variable=self.q, showvalue=0, length=200, bg=p["card"], fg=p["ink"],
                 troughcolor=p["field"], highlightthickness=0, bd=0,
                 command=lambda _v: self._on_quality()).pack(anchor="w")

        # 통계 + 글자수
        self.stats = tk.Label(self, text="", bg=p["card"], fg=p["sub"],
                              font=("Segoe UI", 9), anchor="w", justify="left")
        self.stats.pack(anchor="w", pady=(6, 2))
        self.outcount = tk.Label(self, text=_chars(0), bg=p["card"], fg=p["sub"],
                                 font=("Segoe UI", 9))
        self.outcount.pack(anchor="e")

        # 디코딩
        tk.Frame(self, bg=p["hair"], height=1, width=INNER).pack(fill="x", pady=12)
        tk.Label(self, text="Base64 → 이미지", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.dec = tk.Text(self, height=4, width=46, bg=p["field"], fg=p["ink"],
                           bd=0, relief="flat", wrap="char", insertbackground=p["ink"])
        self.dec.pack(fill="x", pady=(6, 6))
        self.incount = tk.Label(self, text=_chars(0), bg=p["card"], fg=p["sub"],
                                font=("Segoe UI", 9))
        self.incount.pack(anchor="e")
        self.dec.bind("<KeyRelease>", lambda e: self._upd_incount())
        self.dec.bind("<<Paste>>", lambda e: self.after(10, self._upd_incount))
        W.RoundButton(self, "이미지로 저장", self._save, p, "primary", w=INNER, h=38).pack()

        self._reencode()  # 최초 인코딩

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

    def _upd_incount(self):
        try:
            n = len(self.dec.get("1.0", "end-1c"))
            self.incount.configure(text=_chars(n))
        except tk.TclError:
            pass

    def _on_quality(self):
        self.qlabel.configure(text="압축 품질 %d%%" % int(round(self.q.get() * 100)))
        if self.do_comp.get():
            if self._qpend is not None:
                try:
                    self.after_cancel(self._qpend)
                except Exception:
                    pass
            self._qpend = self.after(400, self._reencode)   # 슬라이더 디바운스

    def _reencode(self):
        self._qpend = None
        self.qframe.pack_forget()
        if self.do_comp.get():
            self.qframe.pack(anchor="w", pady=(2, 0), before=self.stats)
        if not self.files:
            return
        self._seq += 1
        seq = self._seq
        comp, q, src = self.do_comp.get(), self.q.get(), self.files[0]
        threading.Thread(target=self._enc_work, args=(src, comp, q, seq), daemon=True).start()

    def _enc_work(self, src, comp, q, seq):
        try:
            if comp:
                r = b64tool.to_data_uri_compressed(src, 1920, q)
                note = " → 압축 %s (%d×%d)" % (W.human(r["comp_bytes"]), r["w"], r["h"])
            else:
                v = b64tool.variants(src)
                r = {"datauri": v["datauri"], "imgtag": v["imgtag"], "css": v["css"],
                     "orig_bytes": os.path.getsize(src), "comp_bytes": 0}
                note = ""
        except Exception as e:
            msg = "변환 실패: %s" % str(e)[:40]
            self._post(lambda: self._apply_err(msg, seq))
            return
        self._post(lambda: self._apply_enc(r, note, seq))

    def _apply_enc(self, r, note, seq):
        if seq != self._seq or not self.winfo_exists():
            return
        self._variants = {"datauri": r["datauri"], "imgtag": r["imgtag"], "css": r["css"]}
        self.enc.delete("1.0", "end")
        self.enc.insert("1.0", r["datauri"])
        n = len(r["datauri"])
        self.outcount.configure(text=_chars(n))
        growth = int(round((n / float(r["orig_bytes"]) - 1) * 100)) if r["orig_bytes"] else 0
        self.stats.configure(text="원본 %s%s → 문자열 %s (%s%d%%)" % (
            W.human(r["orig_bytes"]), note, W.human(n), "+" if growth >= 0 else "−", abs(growth)))
        self.recenter()

    def _apply_err(self, msg, seq):
        if seq != self._seq or not self.winfo_exists():
            return
        self.stats.configure(text=msg)

    def _post(self, fn):
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except (tk.TclError, RuntimeError):
            pass
