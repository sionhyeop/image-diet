"""이미지 다이어트 — 탭 창 (압축/Base64/SVG/PDF). 진입점.
사용법: pythonw compress_gui.pyw <이미지경로> ..."""
import os
import sys
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import singleinstance
import widgets as W
from view_compress import CompressView
from view_base64 import Base64View
from view_svg import SvgView
from view_pdf import PdfView

HERE = os.path.dirname(os.path.abspath(__file__))
TABS = [("압축", CompressView), ("Base64", Base64View), ("SVG", SvgView), ("PDF", PdfView)]


class Toolkit:
    def __init__(self, root, files):
        self.root, self.files = root, files
        p = self.pal = W.palette(W.is_dark())
        root.title("이미지 다이어트")
        root.configure(bg=p["card"])
        root.resizable(False, False)
        try:
            root.iconbitmap(os.path.join(HERE, "assets", "imagediet.ico"))
        except Exception:
            pass
        card = tk.Frame(root, bg=p["card"]); card.pack(padx=18, pady=18)
        hdr = tk.Frame(card, bg=p["card"]); hdr.pack(fill="x")
        self._logo = None
        try:
            self._logo = tk.PhotoImage(file=os.path.join(HERE, "assets", "logo32.png"))
            tk.Label(hdr, image=self._logo, bg=p["card"]).pack(side="left")
        except Exception:
            pass
        tk.Label(hdr, text="  이미지 다이어트", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(hdr, text="파일 %d개" % len(files), bg=p["card"], fg=p["sub"],
                 font=("Segoe UI", 9)).pack(side="right")
        # 탭 바
        self.tabbar = W.Segmented(card, [(t[0], str(i)) for i, t in enumerate(TABS)],
                                  "0", p, w=360, h=34)
        self.tabbar.pack(fill="x", pady=(12, 12))
        self.tabbar.bind("<Button-1>", self._on_tab, add="+")
        self.host = tk.Frame(card, bg=p["card"]); self.host.pack(fill="x")
        self._cur = None
        self._show(0)
        self._center()

    def _on_tab(self, _e):
        self.root.after(1, lambda: self._show(int(self.tabbar.value)))

    def _show(self, idx):
        if self._cur is not None:
            self._cur.destroy()
        View = TABS[idx][1]
        self._cur = View(self.host, self.pal, self.files, self._center)
        self._cur.pack(fill="x")
        self._center()

    def _center(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 3
        self.root.geometry("+%d+%d" % (x, y))


def main():
    argv = [a for a in sys.argv[1:] if os.path.isfile(a)]
    files = singleinstance.coalesce(argv)
    if files is None:
        return  # 형제 인스턴스 — 서버로 전달 후 종료
    if not files:
        root = tk.Tk(); root.withdraw()
        messagebox.showinfo("이미지 다이어트", "압축할 이미지를 선택한 뒤 우클릭하세요.")
        return
    root = tk.Tk()
    Toolkit(root, files)
    root.mainloop()


if __name__ == "__main__":
    main()
