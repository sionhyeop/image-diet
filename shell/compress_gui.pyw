"""이미지 다이어트 — 탐색기 우클릭용 작은 창.
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
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            d = json.load(f)
            return int(d.get("target_kb", 200)), str(d.get("out_format", "auto"))
    except Exception:
        return 200, "auto"


def save_settings(target_kb, out_format):
    try:
        os.makedirs(_CFG_DIR, exist_ok=True)
        with open(_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump({"target_kb": target_kb, "out_format": out_format}, f)
    except Exception:
        pass


class App:
    def __init__(self, root, files):
        self.root = root
        self.files = files
        self.running = False
        root.title("이미지 다이어트")
        root.resizable(False, False)

        target0, fmt0 = load_settings()
        frm = ttk.Frame(root, padding=14)
        frm.grid()

        ttk.Label(frm, text=f"파일 {len(files)}개 선택됨").grid(
            column=0, row=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(frm, text="목표 용량").grid(column=0, row=1, sticky="w")
        self.kb = tk.StringVar(value=str(target0))
        ttk.Entry(frm, textvariable=self.kb, width=8).grid(column=1, row=1, sticky="w")
        ttk.Label(frm, text="KB").grid(column=2, row=1, sticky="w")

        ttk.Label(frm, text="출력 형식").grid(column=0, row=2, sticky="w", pady=(6, 0))
        self.fmt = tk.StringVar(value=fmt0)
        labels = [l for l, _ in FORMATS]
        self.fmt_label = tk.StringVar(
            value=next(l for l, v in FORMATS if v == fmt0))
        cb = ttk.Combobox(frm, textvariable=self.fmt_label, values=labels,
                          state="readonly", width=14)
        cb.grid(column=1, row=2, columnspan=2, sticky="w", pady=(6, 0))

        self.go = ttk.Button(frm, text="압축", command=self.start)
        self.go.grid(column=1, row=3, sticky="w", pady=10)
        ttk.Button(frm, text="취소", command=root.destroy).grid(
            column=2, row=3, sticky="w", pady=10)

        self.status = tk.Text(frm, width=42, height=min(10, max(3, len(files))),
                              state="disabled")
        self.status.grid(column=0, row=4, columnspan=3, sticky="we")

    def _fmt_value(self):
        label = self.fmt_label.get()
        return next(v for l, v in FORMATS if l == label)

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
        threading.Thread(target=self._run, args=(target, fmt), daemon=True).start()

    def _run(self, target, fmt):
        for path in self.files:
            name = os.path.basename(path)
            self.root.after(0, self.log, f"{name} → 처리 중…")
            res = compress.compress_image(path, target, fmt)
            if res.get("ok"):
                self.root.after(0, self.log,
                                f"  ✓ {os.path.basename(res['out_path'])}  {res['size_kb']}KB")
            else:
                self.root.after(0, self.log, f"  ✗ 실패: {res.get('error','')[:40]}")
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
