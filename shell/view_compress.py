"""압축 탭."""
import os
import threading
import tkinter as tk
from tkinter import messagebox
import compress
import widgets as W

FORMATS = [("자동", "auto"), ("WebP", "webp"), ("JPEG", "jpeg"), ("PNG", "png")]
INNER = 360


class CompressView(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        self.kb = tk.StringVar(value="200")
        self._show_settings()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _show_settings(self):
        p = self.pal
        self._clear()
        opts = tk.Frame(self, bg=p["card"]); opts.pack(fill="x")
        opts.grid_columnconfigure(0, minsize=74)
        tk.Label(opts, text="목표 용량", bg=p["card"], fg=p["sub"],
                 font=("Segoe UI", 10), anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        cell = tk.Frame(opts, bg=p["card"]); cell.grid(row=0, column=1, sticky="w", pady=4)
        fcv = tk.Canvas(cell, width=66, height=34, bg=p["card"], highlightthickness=0); fcv.pack(side="left")
        W.round_rect(fcv, 1, 1, 65, 33, 9, fill=p["field"], outline=p["field_line"])
        ent = tk.Entry(fcv, textvariable=self.kb, bd=0, bg=p["field"], fg=p["ink"],
                       font=("Segoe UI", 12, "bold"), justify="center", width=4, insertbackground=p["ink"])
        fcv.create_window(33, 17, window=ent)
        tk.Label(cell, text="KB", bg=p["card"], fg=p["sub"], font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))
        tk.Label(opts, text="출력 형식", bg=p["card"], fg=p["sub"], font=("Segoe UI", 10),
                 anchor="w").grid(row=1, column=0, sticky="w", pady=(10, 4))
        self.seg = W.Segmented(opts, FORMATS, "auto", p, w=INNER - 74)
        self.seg.grid(row=1, column=1, sticky="w", pady=(10, 4))
        act = tk.Frame(self, bg=p["card"]); act.pack(fill="x", pady=(16, 0))
        W.RoundButton(act, "압축", self._start, p, "primary", w=INNER - 100, h=40).pack(side="left")
        W.RoundButton(act, "취소", self.winfo_toplevel().destroy, p, "ghost", w=92, h=40).pack(side="right")

    def _start(self):
        try:
            target = int(self.kb.get())
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("이미지 다이어트", "목표 용량은 양의 정수여야 합니다.")
            return
        fmt = self.seg.value
        self._show_progress()
        threading.Thread(target=self._run, args=(target, fmt), daemon=True).start()

    def _show_progress(self):
        p = self.pal
        self._clear()
        self.bar = W.Bar(self, p, w=INNER); self.bar.pack(fill="x", pady=(2, 12)); self.bar.set(0)
        self.results = tk.Frame(self, bg=p["card"]); self.results.pack(fill="x")
        self.tail = tk.Frame(self, bg=p["card"]); self.tail.pack(fill="x")
        self.recenter()

    def _row(self, name, ok, detail):
        p = self.pal
        row = tk.Frame(self.results, bg=p["card"]); row.pack(fill="x", pady=3)
        tk.Label(row, text=W.elide(name), bg=p["card"], fg=p["ink"], font=("Segoe UI", 10),
                 anchor="w").pack(side="left", fill="x", expand=True)
        if ok:
            W.chip(row, "✓ " + detail, p["ok"], p["ok_soft"], p["card"]).pack(side="right")
        else:
            W.chip(row, "✗ " + detail, p["warn"], p["warn_soft"], p["card"]).pack(side="right")

    def _finish(self, done, orig, comp):
        p = self.pal
        if done and orig > 0:
            pct = max(0, round((1 - comp / float(orig)) * 100))
            cv = tk.Canvas(self.tail, width=INNER, height=40, bg=p["card"], highlightthickness=0)
            cv.pack(fill="x", pady=(12, 0))
            W.round_rect(cv, 1, 1, INNER - 1, 39, 10, fill=p["accent_soft"], outline="")
            cv.create_text(14, 20, text="%s → %s" % (W.human(orig), W.human(comp)),
                           fill=p["ink"], font=("Segoe UI", 10, "bold"), anchor="w")
            cv.create_text(INNER - 14, 20, text="%d%% 가벼워짐 ↓" % pct,
                           fill=p["accent2"], font=("Segoe UI", 10, "bold"), anchor="e")
        b = tk.Frame(self.tail, bg=p["card"]); b.pack(fill="x", pady=(14, 0))
        W.RoundButton(b, "닫기", self.winfo_toplevel().destroy, p, "primary", w=INNER, h=40).pack()
        self.recenter()

    def _run(self, target, fmt):
        total = len(self.files); done = osum = csum = 0
        for i, path in enumerate(self.files):
            try:
                osz = os.path.getsize(path)
            except OSError:
                osz = 0
            res = compress.compress_image(path, target, fmt)
            if res.get("ok"):
                try:
                    csz = os.path.getsize(res["out_path"])
                except OSError:
                    csz = res.get("size_kb", 0) * 1024
                done += 1; osum += osz; csum += csz
                self.after(0, self._row, os.path.basename(path),
                           True, "%s → %s" % (W.human(osz), W.human(csz)))
            else:
                self.after(0, self._row, os.path.basename(path), False,
                           (res.get("error", "") or "실패")[:18])
            self.after(0, self.bar.set, (i + 1) / float(total))
        self.after(0, self._finish, done, osum, csum)
