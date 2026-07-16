"""이미지 다이어트 — 탐색기 우클릭용 팝업 창.
라운드 카드·버튼, 세그먼트 형식 선택, 상태 칩, 절감량 요약 (틸 팔레트, 다크모드 자동).
사용법: pythonw compress_gui.pyw <이미지경로> [<이미지경로> ...]"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compress  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FORMATS = [("자동", "auto"), ("WebP", "webp"), ("JPEG", "jpeg"), ("PNG", "png")]
INNER = 324  # 카드 내부 콘텐츠 폭(px)

_CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                        "image-diet-shell")
_CFG_PATH = os.path.join(_CFG_DIR, "settings.json")


# ───────────────────────── 설정 저장/복원 ─────────────────────────
def load_settings():
    valid = {v for _, v in FORMATS}
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            d = json.load(f)
            fmt = str(d.get("out_format", "auto"))
            if fmt not in valid:
                fmt = "auto"
            return int(d.get("target_kb", 200)), fmt
    except Exception:
        return 200, "auto"


def save_settings(target_kb, out_format):
    try:
        os.makedirs(_CFG_DIR, exist_ok=True)
        with open(_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump({"target_kb": target_kb, "out_format": out_format}, f)
    except Exception:
        pass


# ───────────────────────── 팔레트 ─────────────────────────
def _is_dark():
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return v == 0
    except Exception:
        return False


def _palette(dark):
    if dark:
        return dict(card="#1a2429", ink="#e7eef0", sub="#8ba3ab", hair="#2a373d",
                    field="#212d33", field_line="#33434a", accent="#2dd4bf",
                    accent2="#5eead4", accent_soft="#12332f", on_accent="#06201d",
                    ok="#4ade80", ok_soft="#10331d", warn="#f87171", warn_soft="#3a1c1c")
    return dict(card="#ffffff", ink="#16272d", sub="#5d757d", hair="#dde5e8",
                field="#f3f7f8", field_line="#d3dee1", accent="#0d9488",
                accent2="#0f766e", accent_soft="#d6f0ec", on_accent="#ffffff",
                ok="#16a34a", ok_soft="#dcfce7", warn="#dc2626", warn_soft="#fee2e2")


def _human(n):
    if n >= 1024 * 1024:
        return "%.1fMB" % (n / 1048576.0)
    if n >= 1024:
        return "%dKB" % round(n / 1024.0)
    return "%dB" % n


# ───────────────────────── Canvas 유틸 ─────────────────────────
def _round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def _chip(parent, text, fg, bg, cardbg):
    cv = tk.Canvas(parent, height=22, bg=cardbg, highlightthickness=0)
    t = cv.create_text(11, 12, text=text, fill=fg,
                       font=("Segoe UI", 9, "bold"), anchor="w")
    x1, _y1, x2, _y2 = cv.bbox(t)
    w = (x2 - x1) + 22
    cv.configure(width=w)
    rr = _round_rect(cv, 1, 2, w - 1, 20, 9, fill=bg, outline="")
    cv.tag_lower(rr)
    return cv


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
        self._rect = _round_rect(self, 1, 1, w - 1, h - 1, 10,
                                 fill=self._fill, outline=outline)
        self.create_text(w // 2, h // 2, text=text, fill=self._fg,
                         font=("Segoe UI", 11, "bold"))
        self.bind("<Enter>", lambda e: self.itemconfig(self._rect, fill=self._hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self._rect, fill=self._fill))
        self.bind("<Button-1>", lambda e: self.command())


class Segmented(tk.Canvas):
    def __init__(self, parent, options, value, pal, w=INNER, h=34):
        super().__init__(parent, width=w, height=h, bg=pal["card"],
                         highlightthickness=0, cursor="hand2")
        self.options, self.pal, self.value = options, pal, value
        self.w, self.h, self.n = w, h, len(options)
        _round_rect(self, 1, 1, w - 1, h - 1, 9,
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
                self._dyn.append(_round_rect(self, x1, 4, x2, self.h - 4, 7,
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
    def __init__(self, parent, pal, w=INNER, h=6):
        super().__init__(parent, width=w, height=h, bg=pal["card"],
                         highlightthickness=0)
        self.w, self.h, self.pal = w, h, pal
        _round_rect(self, 0, 0, w, h, h // 2, fill=pal["field"], outline="")
        self._fill = None

    def set(self, frac):
        if self._fill:
            self.delete(self._fill)
        fw = max(self.h, int(self.w * max(0.0, min(1.0, frac))))
        self._fill = _round_rect(self, 0, 0, fw, self.h, self.h // 2,
                                 fill=self.pal["accent"], outline="")


def _elide(name, keep=30):
    if len(name) <= keep:
        return name
    return name[:keep - 14] + "…" + name[-13:]


# ───────────────────────── 앱 ─────────────────────────
class App:
    def __init__(self, root, files):
        self.root = root
        self.files = files
        p = self.pal = _palette(_is_dark())

        root.title("이미지 다이어트")
        root.configure(bg=p["card"])
        root.resizable(False, False)
        try:
            root.iconbitmap(os.path.join(HERE, "assets", "imagediet.ico"))
        except Exception:
            pass

        card = tk.Frame(root, bg=p["card"])
        card.pack(padx=18, pady=18)

        # 헤더
        hdr = tk.Frame(card, bg=p["card"])
        hdr.pack(fill="x")
        self._logo = None
        try:
            self._logo = tk.PhotoImage(file=os.path.join(HERE, "assets", "logo32.png"))
            tk.Label(hdr, image=self._logo, bg=p["card"]).pack(side="left")
        except Exception:
            pass
        htext = tk.Frame(hdr, bg=p["card"])
        htext.pack(side="left", padx=(11, 0))
        tk.Label(htext, text="이미지 다이어트", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.sub = tk.Label(htext, text="파일 %d개 선택됨" % len(files),
                            bg=p["card"], fg=p["sub"], font=("Segoe UI", 9))
        self.sub.pack(anchor="w")

        tk.Frame(card, bg=p["hair"], height=1, width=INNER).pack(fill="x", pady=(14, 12))

        self.body = tk.Frame(card, bg=p["card"])
        self.body.pack(fill="x")
        self._show_settings()
        self._center()

    def _clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def _center(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 3
        self.root.geometry("+%d+%d" % (x, y))

    # ── 설정 화면 ──
    def _show_settings(self):
        p = self.pal
        self._clear_body()
        opts = tk.Frame(self.body, bg=p["card"])
        opts.pack(fill="x")
        opts.grid_columnconfigure(0, minsize=74)

        tk.Label(opts, text="목표 용량", bg=p["card"], fg=p["sub"],
                 font=("Segoe UI", 10), anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        kbcell = tk.Frame(opts, bg=p["card"])
        kbcell.grid(row=0, column=1, sticky="w", pady=4)
        target0, fmt0 = load_settings()
        self.kb = tk.StringVar(value=str(target0))
        fcv = tk.Canvas(kbcell, width=66, height=34, bg=p["card"], highlightthickness=0)
        fcv.pack(side="left")
        _round_rect(fcv, 1, 1, 65, 33, 9, fill=p["field"], outline=p["field_line"])
        ent = tk.Entry(fcv, textvariable=self.kb, bd=0, bg=p["field"], fg=p["ink"],
                       font=("Segoe UI", 12, "bold"), justify="center", width=4,
                       insertbackground=p["ink"])
        fcv.create_window(33, 17, window=ent)
        tk.Label(kbcell, text="KB", bg=p["card"], fg=p["sub"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

        tk.Label(opts, text="출력 형식", bg=p["card"], fg=p["sub"],
                 font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="w", pady=(10, 4))
        self.seg = Segmented(opts, FORMATS, fmt0, p, w=INNER - 74)
        self.seg.grid(row=1, column=1, sticky="w", pady=(10, 4))

        actions = tk.Frame(self.body, bg=p["card"])
        actions.pack(fill="x", pady=(16, 0))
        RoundButton(actions, "압축", self.start, p, "primary", w=224, h=40).pack(side="left")
        RoundButton(actions, "취소", self.root.destroy, p, "ghost", w=92, h=40).pack(side="right")

    # ── 실행 ──
    def start(self):
        try:
            target = int(self.kb.get())
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("이미지 다이어트", "목표 용량은 양의 정수여야 합니다.")
            return
        fmt = self.seg.value
        save_settings(target, fmt)
        self._show_progress()
        threading.Thread(target=self._run, args=(target, fmt), daemon=True).start()

    def _show_progress(self):
        p = self.pal
        self._clear_body()
        self.sub.configure(text="압축하는 중…")
        self.bar = Bar(self.body, p, w=INNER)
        self.bar.pack(fill="x", pady=(2, 12))
        self.bar.set(0)
        self.results = tk.Frame(self.body, bg=p["card"])
        self.results.pack(fill="x")
        self.tail = tk.Frame(self.body, bg=p["card"])
        self.tail.pack(fill="x")

    def _add_result(self, name, ok, detail):
        p = self.pal
        row = tk.Frame(self.results, bg=p["card"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=_elide(name), bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 10), anchor="w").pack(side="left", fill="x", expand=True)
        if ok:
            _chip(row, "✓ " + detail, p["ok"], p["ok_soft"], p["card"]).pack(side="right")
        else:
            _chip(row, "✗ " + detail, p["warn"], p["warn_soft"], p["card"]).pack(side="right")

    def _finish(self, done, orig, comp):
        p = self.pal
        self.sub.configure(text="%d개 처리 완료" % done)
        if done and orig > 0:
            pct = max(0, round((1 - comp / float(orig)) * 100))
            cv = tk.Canvas(self.tail, width=INNER, height=40, bg=p["card"],
                           highlightthickness=0)
            cv.pack(fill="x", pady=(12, 0))
            _round_rect(cv, 1, 1, INNER - 1, 39, 10, fill=p["accent_soft"], outline="")
            cv.create_text(14, 20, text="%s → %s" % (_human(orig), _human(comp)),
                           fill=p["ink"], font=("Segoe UI", 10, "bold"), anchor="w")
            cv.create_text(INNER - 14, 20, text="%d%% 가벼워짐 ↓" % pct,
                           fill=p["accent2"], font=("Segoe UI", 10, "bold"), anchor="e")
        btns = tk.Frame(self.tail, bg=p["card"])
        btns.pack(fill="x", pady=(14, 0))
        RoundButton(btns, "닫기", self.root.destroy, p, "primary", w=INNER, h=40).pack()
        self._center()

    def _run(self, target, fmt):
        total = len(self.files)
        done = orig_sum = comp_sum = 0
        for i, path in enumerate(self.files):
            try:
                osize = os.path.getsize(path)
            except OSError:
                osize = 0
            res = compress.compress_image(path, target, fmt)
            if res.get("ok"):
                try:
                    csize = os.path.getsize(res["out_path"])
                except OSError:
                    csize = res.get("size_kb", 0) * 1024
                done += 1
                orig_sum += osize
                comp_sum += csize
                self.root.after(0, self._add_result,
                                os.path.basename(res["out_path"]), True, _human(csize))
            else:
                self.root.after(0, self._add_result,
                                os.path.basename(path), False,
                                (res.get("error", "") or "실패")[:20])
            self.root.after(0, self.bar.set, (i + 1) / float(total))
        self.root.after(0, self._finish, done, orig_sum, comp_sum)


def main():
    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if not files:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("이미지 다이어트", "압축할 이미지를 선택한 뒤 우클릭하세요.")
        return
    root = tk.Tk()
    App(root, files)
    root.mainloop()


if __name__ == "__main__":
    main()
