"""이미지 다이어트 — 탐색기 우클릭용 팝업 창 (크롬 익스텐션 톤).
사용법: pythonw compress_gui.pyw <이미지경로> [<이미지경로> ...]"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compress  # noqa: E402

FORMATS = [("자동 (WebP)", "auto"), ("WebP", "webp"),
           ("JPEG", "jpeg"), ("PNG", "png")]
_CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                        "image-diet-shell")
_CFG_PATH = os.path.join(_CFG_DIR, "settings.json")


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


def _is_dark():
    """Windows 앱 테마: AppsUseLightTheme=0 이면 다크."""
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return v == 0
    except Exception:
        return False


# 색 팔레트 (라이트/다크)
def _palette(dark):
    if dark:
        return dict(bg="#202124", card="#292a2d", fg="#e8eaed",
                    sub="#9aa0a6", border="#3c4043", accent="#8ab4f8",
                    accent_fg="#202124", field="#303134")
    return dict(bg="#f1f3f4", card="#ffffff", fg="#202124",
                sub="#5f6368", border="#dadce0", accent="#1a73e8",
                accent_fg="#ffffff", field="#ffffff")


class App:
    def __init__(self, root, files):
        self.root = root
        self.files = files
        self.running = False
        self.pal = _palette(_is_dark())
        p = self.pal

        root.title("이미지 다이어트")
        root.configure(bg=p["bg"])
        root.resizable(False, False)
        try:
            root.iconbitmap(os.path.join(os.path.dirname(__file__),
                                         "assets", "imagediet.ico"))
        except Exception:
            pass

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Card.TFrame", background=p["card"])
        style.configure("Card.TLabel", background=p["card"], foreground=p["fg"])
        style.configure("Sub.TLabel", background=p["card"], foreground=p["sub"])
        style.configure("Accent.TButton", background=p["accent"],
                        foreground=p["accent_fg"], borderwidth=0, focusthickness=0,
                        padding=(16, 8), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", p["accent"]), ("pressed", p["accent"])])
        style.configure("Ghost.TButton", background=p["card"], foreground=p["sub"],
                        borderwidth=1, padding=(14, 8))
        style.configure("TCombobox", fieldbackground=p["field"],
                        background=p["field"], foreground=p["fg"])
        style.configure("Diet.Horizontal.TProgressbar",
                        background=p["accent"], troughcolor=p["field"], borderwidth=0)

        # 외곽 여백 + 카드
        outer = tk.Frame(root, bg=p["bg"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.pack(fill="both", expand=True)

        # 헤더 (로고 + 제목)
        header = ttk.Frame(card, style="Card.TFrame")
        header.grid(column=0, row=0, columnspan=3, sticky="w", pady=(0, 14))
        self._logo = None
        try:
            self._logo = tk.PhotoImage(file=os.path.join(
                os.path.dirname(__file__), "assets", "logo32.png"))
            ttk.Label(header, image=self._logo, style="Card.TLabel").pack(side="left")
        except Exception:
            pass
        ttk.Label(header, text="  이미지 다이어트", style="Card.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(side="left")

        target0, fmt0 = load_settings()
        ttk.Label(card, text=f"파일 {len(files)}개 선택됨", style="Sub.TLabel").grid(
            column=0, row=1, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(card, text="목표 용량", style="Card.TLabel").grid(
            column=0, row=2, sticky="w", pady=4)
        self.kb = tk.StringVar(value=str(target0))
        tk.Entry(card, textvariable=self.kb, width=8, bg=p["field"], fg=p["fg"],
                 relief="flat", highlightthickness=1, highlightbackground=p["border"],
                 insertbackground=p["fg"]).grid(column=1, row=2, sticky="w", pady=4)
        ttk.Label(card, text="KB", style="Sub.TLabel").grid(column=2, row=2, sticky="w")

        ttk.Label(card, text="출력 형식", style="Card.TLabel").grid(
            column=0, row=3, sticky="w", pady=4)
        self.fmt_label = tk.StringVar(value=next(l for l, v in FORMATS if v == fmt0))
        ttk.Combobox(card, textvariable=self.fmt_label, values=[l for l, _ in FORMATS],
                     state="readonly", width=14).grid(
            column=1, row=3, columnspan=2, sticky="w", pady=4)

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.grid(column=0, row=4, columnspan=3, sticky="e", pady=(14, 6))
        ttk.Button(btns, text="취소", style="Ghost.TButton",
                   command=root.destroy).pack(side="right", padx=(8, 0))
        self.go = ttk.Button(btns, text="압축", style="Accent.TButton", command=self.start)
        self.go.pack(side="right")

        self.prog = ttk.Progressbar(card, style="Diet.Horizontal.TProgressbar",
                                    mode="determinate", maximum=len(files))
        self.prog.grid(column=0, row=5, columnspan=3, sticky="we", pady=(6, 6))
        self.status = tk.Text(card, width=40, height=min(8, max(2, len(files))),
                              bg=p["card"], fg=p["fg"], relief="flat",
                              highlightthickness=0, state="disabled", wrap="none")
        self.status.grid(column=0, row=6, columnspan=3, sticky="we")

    def _fmt_value(self):
        return next(v for l, v in FORMATS if l == self.fmt_label.get())

    def log(self, line):
        self.status.configure(state="normal")
        self.status.insert("end", line + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def start(self):
        if self.running:
            return
        try:
            target = int(self.kb.get())
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("이미지 다이어트", "목표 용량은 양의 정수여야 합니다.")
            return
        fmt = self._fmt_value()
        save_settings(target, fmt)
        self.running = True
        self.go.configure(state="disabled")
        self.prog.configure(value=0)
        threading.Thread(target=self._run, args=(target, fmt), daemon=True).start()

    def _run(self, target, fmt):
        for i, path in enumerate(self.files):
            name = os.path.basename(path)
            res = compress.compress_image(path, target, fmt)
            if res.get("ok"):
                msg = f"✓ {os.path.basename(res['out_path'])}  {res['size_kb']}KB"
            else:
                msg = f"✗ {name}: {res.get('error', '')[:38]}"
            self.root.after(0, self.log, msg)
            self.root.after(0, lambda v=i + 1: self.prog.configure(value=v))
        self.root.after(0, self.log, "완료")
        self.root.after(0, lambda: self.go.configure(state="normal"))
        self.running = False


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
