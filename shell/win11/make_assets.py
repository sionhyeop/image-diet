"""icon-512.png -> 메뉴 .ico + MSIX 로고 PNG 생성."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SRC = os.path.join(HERE, "..", "..", "icon-512.png")


def main():
    os.makedirs(ASSETS, exist_ok=True)
    src = Image.open(SRC).convert("RGBA")

    # 메뉴/창 아이콘 (.ico, 다중 해상도)
    src.save(os.path.join(ASSETS, "imagediet.ico"),
             sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (256, 256)])

    # 창 헤더 로고 (Tk PhotoImage는 PNG)
    src.resize((32, 32), Image.LANCZOS).save(os.path.join(ASSETS, "logo32.png"))

    # MSIX 필수 로고
    src.resize((44, 44), Image.LANCZOS).save(os.path.join(ASSETS, "Square44x44Logo.png"))
    src.resize((150, 150), Image.LANCZOS).save(os.path.join(ASSETS, "Square150x150Logo.png"))
    src.resize((50, 50), Image.LANCZOS).save(os.path.join(ASSETS, "StoreLogo.png"))
    print("assets written to", ASSETS)


if __name__ == "__main__":
    main()
