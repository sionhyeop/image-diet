# 탐색기 우클릭 이미지 압축 (Image Diet Shell) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 웹앱 "이미지 다이어트"의 압축 기능을 Windows 탐색기 우클릭 → 작은 창 → 같은 폴더에 저장 흐름으로 제공한다.

**Architecture:** 순수 Python 압축 엔진(`compress.py`, Pillow)을 만들고, 그 위에 Tkinter 작은 창(`compress_gui.pyw`)을 얹는다. 우클릭 메뉴는 `HKEY_CURRENT_USER` 레지스트리(`.reg`)로 등록하며 `install.bat`이 Windows의 `pythonw.exe` 경로를 자동으로 채워 넣는다. 원본은 절대 변경하지 않고, 결과는 원본과 같은 폴더에 접미사 없이 숫자만 붙여 저장한다.

**Tech Stack:** Python 3.13(Windows 실행) / 3.14(WSL 테스트), Pillow, Tkinter(내장), Windows 레지스트리(.reg + .bat)

## Global Constraints

- 원본 파일은 절대 덮어쓰거나 수정하지 않는다.
- 결과 파일은 원본과 **같은 폴더**, 접미사 없이 **숫자만** 붙인다: `photo.jpg` → `photo1.webp`, 충돌 시 `photo2.webp`, `photo3.webp` …
- 창 옵션은 **목표 용량(KB)** 과 **출력 형식**(auto/webp/jpeg/png) 2개뿐. 품질 슬라이더·해상도 제한 옵션 없음.
- 레지스트리는 `HKEY_CURRENT_USER`만 사용 (관리자 권한·시스템 전역 변경 금지).
- 여러 파일 선택 후 우클릭 시 한 창에서 같은 설정으로 일괄 처리한다.
- "auto" 형식은 WebP 우선(웹앱과 동일), 투명 이미지는 WebP로 투명 유지.
- 신규 파일은 저장소 내 `shell/` 폴더에 둔다.
- 테스트는 WSL에서 `python3`(Pillow 12, webp 지원)로 실행한다.

---

### Task 1: 출력 경로 · 형식 결정 헬퍼

원본을 건드리지 않고 안전한 새 파일명을 만들고, "auto"를 구체 형식으로 바꾸는 순수 함수. 이후 모든 작업의 기반.

**Files:**
- Create: `shell/compress.py`
- Test: `shell/test_compress.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `EXT_FOR_FORMAT: dict[str, str]` — `{"webp": ".webp", "jpeg": ".jpg", "png": ".png"}`
  - `resolve_format(src_path: str, out_format: str) -> str` — `out_format`이 `"auto"`면 `"webp"` 반환, 그 외("webp"/"jpeg"/"png")는 그대로 소문자로 반환.
  - `numbered_output_path(src_path: str, out_ext: str) -> str` — 원본과 같은 폴더에 `<stem><n><out_ext>`를 만들되, 존재하지 않는 가장 작은 `n≥1`을 사용. `out_ext`는 `.webp`처럼 점 포함.

- [ ] **Step 1: Write the failing test**

`shell/test_compress.py`:

```python
import os
from PIL import Image
import compress


def test_resolve_format_auto_is_webp():
    assert compress.resolve_format("x.png", "auto") == "webp"


def test_resolve_format_passthrough():
    assert compress.resolve_format("x.png", "JPEG") == "jpeg"
    assert compress.resolve_format("x.png", "png") == "png"


def test_numbered_output_path_first(tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"x")
    out = compress.numbered_output_path(str(src), ".webp")
    assert out == str(tmp_path / "photo1.webp")


def test_numbered_output_path_avoids_collision(tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"x")
    (tmp_path / "photo1.webp").write_bytes(b"x")
    (tmp_path / "photo2.webp").write_bytes(b"x")
    out = compress.numbered_output_path(str(src), ".webp")
    assert out == str(tmp_path / "photo3.webp")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "shell" && python3 -m pytest test_compress.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compress'` 또는 `AttributeError`.

- [ ] **Step 3: Write minimal implementation**

`shell/compress.py`:

```python
"""이미지 다이어트 압축 엔진 (UI 없음). Pillow 기반 순수 함수 모음."""
import os

EXT_FOR_FORMAT = {"webp": ".webp", "jpeg": ".jpg", "png": ".png"}


def resolve_format(src_path: str, out_format: str) -> str:
    fmt = (out_format or "auto").lower()
    if fmt == "auto":
        return "webp"
    return fmt


def numbered_output_path(src_path: str, out_ext: str) -> str:
    folder = os.path.dirname(os.path.abspath(src_path))
    stem = os.path.splitext(os.path.basename(src_path))[0]
    n = 1
    while True:
        candidate = os.path.join(folder, f"{stem}{n}{out_ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "shell" && python3 -m pytest test_compress.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add shell/compress.py shell/test_compress.py
git commit -m "feat(shell): 출력 경로·형식 결정 헬퍼"
```

---

### Task 2: 압축 엔진 (step-down 리사이즈 + 목표 용량 이진탐색 + 인코딩)

이미지를 목표 용량 이하로 맞춰 실제 파일로 저장하는 핵심 함수. 웹앱 알고리즘(품질 이진탐색 6회 + 미달 시 해상도 0.78배 재시도, step-down 절반 축소)을 포팅.

**Files:**
- Modify: `shell/compress.py`
- Test: `shell/test_compress.py`

**Interfaces:**
- Consumes: `resolve_format`, `numbered_output_path`, `EXT_FOR_FORMAT` (Task 1)
- Produces:
  - `encode_to_bytes(img, fmt: str, quality: int) -> bytes` — PIL 이미지를 `fmt`("webp"/"jpeg"/"png")로 인코딩한 바이트. jpeg/webp는 `quality` 사용, png는 `optimize=True`.
  - `step_down_resize(img, scale: float) -> PIL.Image` — `scale`(0<scale<1)만큼 축소하되, 목표의 2배 이하가 될 때까지 절반씩 LANCZOS로 줄인 뒤 마지막에 목표 크기로.
  - `compress_image(src_path: str, target_kb: int | None, out_format: str) -> dict` — 저장까지 수행. 반환: `{"ok": True, "out_path": str, "size_kb": int}` 또는 실패 시 `{"ok": False, "src_path": str, "error": str}`.

- [ ] **Step 1: Write the failing test**

`shell/test_compress.py`에 추가:

```python
def _make_photo(path, size=(1600, 1200)):
    # 노이즈가 있어 쉽게 안 줄어드는 사진 유사 이미지
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        for x in range(0, size[0], 1):
            px[x, y] = ((x * 7) % 256, (y * 13) % 256, ((x + y) * 5) % 256)
    img.save(path, "PNG")


def test_compress_hits_target_webp(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src))
    before = src.read_bytes()
    res = compress.compress_image(str(src), target_kb=60, out_format="auto")
    assert res["ok"] is True
    assert res["out_path"] == str(tmp_path / "shot1.webp")
    assert os.path.exists(res["out_path"])
    assert res["size_kb"] <= 60
    # 원본 미변경
    assert src.read_bytes() == before


def test_compress_jpeg_format(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src), size=(800, 600))
    res = compress.compress_image(str(src), target_kb=40, out_format="jpeg")
    assert res["out_path"].endswith(".jpg")
    with Image.open(res["out_path"]) as im:
        assert im.format == "JPEG"


def test_compress_png_reduces_under_target(tmp_path):
    src = tmp_path / "shot.png"
    _make_photo(str(src), size=(1200, 900))
    res = compress.compress_image(str(src), target_kb=80, out_format="png")
    assert res["ok"] is True
    assert res["size_kb"] <= 80
    assert res["out_path"].endswith(".png")


def test_compress_bad_file_returns_error(tmp_path):
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"not an image")
    res = compress.compress_image(str(bad), target_kb=50, out_format="auto")
    assert res["ok"] is False
    assert "error" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "shell" && python3 -m pytest test_compress.py -v`
Expected: FAIL — `AttributeError: module 'compress' has no attribute 'compress_image'`.

- [ ] **Step 3: Write minimal implementation**

`shell/compress.py`에 추가 (파일 상단 import에 Pillow 추가):

```python
import io
from PIL import Image, ImageOps

_MIN_Q, _MAX_Q, _SEARCH_STEPS = 30, 95, 6
_RES_STEP = 0.78          # 목표 미달 시 해상도 축소 비율
_MAX_RES_RETRIES = 6


def encode_to_bytes(img, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, "PNG", optimize=True)
    elif fmt == "jpeg":
        rgb = img.convert("RGB")
        rgb.save(buf, "JPEG", quality=quality, optimize=True)
    else:  # webp
        img.save(buf, "WEBP", quality=quality, method=6)
    return buf.getvalue()


def step_down_resize(img, scale: float):
    if scale >= 1.0:
        return img
    tw = max(1, round(img.width * scale))
    th = max(1, round(img.height * scale))
    cur = img
    # 목표의 2배 이하가 될 때까지 절반씩
    while cur.width > tw * 2 and cur.height > th * 2:
        cur = cur.resize((cur.width // 2, cur.height // 2), Image.LANCZOS)
    if (cur.width, cur.height) != (tw, th):
        cur = cur.resize((tw, th), Image.LANCZOS)
    return cur


def _best_under_target(img, fmt: str, target_bytes: int) -> bytes:
    """품질 이진탐색으로 target_bytes 이하 중 최고 품질 바이트를 찾음.
    png는 품질 개념이 없어 그대로 인코딩."""
    if fmt == "png":
        return encode_to_bytes(img, fmt, 0)
    lo, hi = _MIN_Q, _MAX_Q
    best = None
    for _ in range(_SEARCH_STEPS):
        mid = (lo + hi) // 2
        data = encode_to_bytes(img, fmt, mid)
        if len(data) <= target_bytes:
            best = data
            lo = mid + 1
        else:
            hi = mid - 1
        if lo > hi:
            break
    if best is not None:
        return best
    # 최저 품질도 초과 → 최저 품질 바이트 반환(해상도 축소는 상위에서)
    return encode_to_bytes(img, fmt, _MIN_Q)


def compress_image(src_path: str, target_kb, out_format: str) -> dict:
    try:
        with Image.open(src_path) as opened:
            img = ImageOps.exif_transpose(opened)
            fmt = resolve_format(src_path, out_format)
            if fmt in ("jpeg",) and img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            if target_kb is None:
                data = encode_to_bytes(img, fmt, 82)
            else:
                target_bytes = int(target_kb) * 1024
                work = img
                data = _best_under_target(work, fmt, target_bytes)
                retries = 0
                while len(data) > target_bytes and retries < _MAX_RES_RETRIES:
                    work = step_down_resize(work, _RES_STEP)
                    data = _best_under_target(work, fmt, target_bytes)
                    retries += 1

            out_ext = EXT_FOR_FORMAT[fmt]
            out_path = numbered_output_path(src_path, out_ext)
            with open(out_path, "wb") as f:
                f.write(data)
            return {"ok": True, "out_path": out_path,
                    "size_kb": max(1, round(len(data) / 1024))}
    except Exception as e:  # 손상 파일 등은 건너뜀
        return {"ok": False, "src_path": src_path, "error": str(e)}
```

파일 상단 기존 `import os` 아래에 `import io`와 `from PIL import Image, ImageOps`가 있는지 확인(위 블록에 포함).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "shell" && python3 -m pytest test_compress.py -v`
Expected: PASS (8 passed). 만약 `test_compress_hits_target_webp`가 근소하게 초과하면 노이즈 이미지 특성이므로 `target_kb`를 키우기보다 `_MAX_RES_RETRIES` 여유가 동작하는지 확인.

- [ ] **Step 5: Commit**

```bash
git add shell/compress.py shell/test_compress.py
git commit -m "feat(shell): 목표 용량 압축 엔진 (step-down 리사이즈+이진탐색)"
```

---

### Task 3: Tkinter 작은 창 (`compress_gui.pyw`)

우클릭으로 넘어온 파일 경로들을 받아 옵션 2개를 입력받고, 엔진을 호출해 일괄 처리하며 결과를 표시. 마지막 설정을 기억.

**Files:**
- Create: `shell/compress_gui.pyw`
- Manual test only (Tkinter 창은 WSL에서 자동 테스트 불가 — Windows에서 수동 확인)

**Interfaces:**
- Consumes: `compress.compress_image(src_path, target_kb, out_format)` (Task 2)
- Produces: 실행 진입점. `pythonw.exe compress_gui.pyw <file1> <file2> ...` 형태로 호출됨.
- 설정 저장 위치: `%APPDATA%\image-diet-shell\settings.json` — `{"target_kb": int, "out_format": str}`.

- [ ] **Step 1: 창 스켈레톤 + 설정 로드/저장 작성**

`shell/compress_gui.pyw`:

```python
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
```

- [ ] **Step 2: 창 UI + 압축 실행 로직 작성**

같은 파일에 이어서:

```python
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
```

- [ ] **Step 3: Windows에서 수동 확인**

Windows PowerShell 또는 CMD에서 (WSL 아님):

```
cd C:\dev\2026 soma\downsizing img\shell
"C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\python.exe" compress_gui.pyw "C:\경로\샘플.jpg"
```

Expected: 작은 창이 뜨고 → 목표 용량 200, 형식 자동 → [압축] → 같은 폴더에 `샘플1.webp` 생성, 창에 `✓ 샘플1.webp  NNKB` 표시. 여러 경로를 인자로 주면 순차 처리되는지 확인.

- [ ] **Step 4: Commit**

```bash
git add shell/compress_gui.pyw
git commit -m "feat(shell): Tkinter 우클릭 압축 창"
```

---

### Task 4: 우클릭 등록 (`install.bat`, `uninstall.reg`)

이미지 확장자 우클릭 메뉴에 항목을 추가. `install.bat`이 `pythonw.exe` 경로와 스크립트 경로를 탐지해 레지스트리에 직접 기록(경로에 공백·역슬래시가 있어 정적 `.reg`보다 배치가 안전).

**Files:**
- Create: `shell/install.bat`
- Create: `shell/uninstall.reg`

**Interfaces:**
- Consumes: `compress_gui.pyw` (Task 3)
- Produces: `HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\<.ext>\shell\ImageDiet` 항목. command = `"<pythonw>" "<...\compress_gui.pyw>" "%1"`.

- [ ] **Step 1: `install.bat` 작성**

`shell/install.bat`:

```bat
@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

rem 이 스크립트가 있는 폴더
set "HERE=%~dp0"
set "GUI=%HERE%compress_gui.pyw"

rem pythonw.exe 탐지: py 런처 우선, 없으면 where
set "PYW="
for /f "delims=" %%p in ('where pythonw.exe 2^>nul') do (
    if not defined PYW set "PYW=%%p"
)
if not defined PYW (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" (
        set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    )
)
if not defined PYW (
    echo pythonw.exe 를 찾을 수 없습니다. Python 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo 엔진: "%PYW%"
echo 스크립트: "%GUI%"

set "MENU=이미지 다이어트로 압축"
for %%E in (.jpg .jpeg .png .webp .bmp) do (
    set "KEY=HKCU\Software\Classes\SystemFileAssociations\%%E\shell\ImageDiet"
    reg add "!KEY!" /ve /d "!MENU!" /f >nul
    reg add "!KEY!" /v Icon /d "\"%PYW%\"" /f >nul
    reg add "!KEY!" /v MultiSelectModel /d "Player" /f >nul
    reg add "!KEY!\command" /ve /d "\"%PYW%\" \"%GUI%\" \"%%1\"" /f >nul
)
echo 완료. 이미지 우클릭 메뉴에 "!MENU!" 가 추가되었습니다.
pause
```

- [ ] **Step 2: `uninstall.reg` 작성**

`shell/uninstall.reg` (앞의 `-`가 키 삭제를 의미):

```
Windows Registry Editor Version 5.00

[-HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\.jpg\shell\ImageDiet]

[-HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\.jpeg\shell\ImageDiet]

[-HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\.png\shell\ImageDiet]

[-HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\.webp\shell\ImageDiet]

[-HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\.bmp\shell\ImageDiet]
```

- [ ] **Step 3: Windows에서 수동 확인**

1. 탐색기에서 `shell\install.bat` 더블클릭 (또는 CMD에서 실행). "완료" 메시지 확인.
2. 아무 `.jpg`/`.png`를 우클릭 → "이미지 다이어트로 압축" 항목이 보이는지 확인 (Win11은 "더 많은 옵션 표시" 안에 있을 수 있음).
3. 클릭 → 창이 뜨고 압축 → 같은 폴더에 숫자 붙은 새 파일 생성 확인.
4. 이미지 2~3개 선택 후 우클릭 → 항목 클릭 → 한 창에서 모두 처리되는지 확인.
5. 제거: `uninstall.reg` 더블클릭 → 메뉴에서 항목이 사라지는지 확인.

> 참고: `MultiSelectModel=Player`는 여러 선택 시 하나의 인스턴스에 파일들을 함께 전달하려는 의도다. Windows 버전에 따라 다중 선택이 파일마다 창을 띄우면, 이 값을 유지하되 각 창이 독립 동작하는 것으로 간주하고 수동 확인 결과를 기록한다(기능상 손상 없음).

- [ ] **Step 4: Commit**

```bash
git add shell/install.bat shell/uninstall.reg
git commit -m "feat(shell): 우클릭 메뉴 등록/해제 스크립트"
```

---

### Task 5: 문서화 (`shell/README.md` + 루트 README 링크)

설치·사용·제거 방법을 남긴다.

**Files:**
- Create: `shell/README.md`
- Modify: `README.md` (기능 목록 아래에 데스크톱 우클릭 안내 한 줄 + 링크)

**Interfaces:**
- Consumes: 앞 태스크 전체
- Produces: (없음)

- [ ] **Step 1: `shell/README.md` 작성**

```markdown
# 이미지 다이어트 — 탐색기 우클릭 압축 (Windows)

웹앱을 열지 않고, 탐색기에서 이미지를 **우클릭**해 바로 압축합니다.

## 요구 사항
- Windows 10/11
- Python 3.x + Pillow (`pip install pillow`)

## 설치
1. `install.bat` 실행 (관리자 권한 불필요).
2. 이미지 파일을 우클릭 → **"이미지 다이어트로 압축"**.

## 사용
- 작은 창에서 **목표 용량(KB)** 과 **출력 형식**(자동/WebP/JPEG/PNG)을 고르고 [압축].
- 결과는 원본과 **같은 폴더**에 `photo1.webp`처럼 숫자만 붙여 저장됩니다. 원본은 그대로.
- 여러 장을 선택해 우클릭하면 같은 설정으로 일괄 처리됩니다.

## 제거
- `uninstall.reg` 더블클릭.

## 구성
| 파일 | 역할 |
| --- | --- |
| `compress.py` | 압축 엔진 (Pillow) |
| `compress_gui.pyw` | Tkinter 작은 창 |
| `install.bat` | 우클릭 메뉴 등록 |
| `uninstall.reg` | 우클릭 메뉴 제거 |
| `test_compress.py` | 엔진 단위 테스트 |
```

- [ ] **Step 2: 루트 `README.md`에 링크 추가**

`README.md`의 기능 목록(`- **PWA + 오프라인** …` 줄) 다음에 아래 한 줄 추가:

```markdown
- **데스크톱 우클릭 압축(Windows)** — 탐색기에서 이미지를 우클릭해 바로 압축. 설치·사용법은 [`shell/README.md`](shell/README.md) 참고
```

- [ ] **Step 3: 테스트 전체 재확인**

Run: `cd "shell" && python3 -m pytest test_compress.py -v`
Expected: PASS (8 passed).

- [ ] **Step 4: Commit**

```bash
git add shell/README.md README.md
git commit -m "docs(shell): 우클릭 압축 설치·사용 문서"
```

---

## Self-Review 결과

- **Spec coverage:** 작은 창(Task 3)·목표 용량+형식 옵션(Task 2,3)·같은 폴더 숫자 파일명(Task 1,2)·일괄 처리(Task 3)·우클릭 등록 HKCU(Task 4)·원본 미변경(Task 2 테스트)·auto=WebP(Task 1,2)·YAGNI 범위(품질 슬라이더/해상도 옵션/무음 모드 제외)·`shell/` 배치·테스트(Task 1,2) 모두 태스크로 커버됨.
- **Placeholder scan:** 코드 스텝은 모두 실제 코드 포함, "적절히 처리" 류 없음. Windows 수동 테스트 스텝은 자동화 불가 영역이라 구체 명령·기대결과로 명시.
- **Type consistency:** `resolve_format`/`numbered_output_path`/`EXT_FOR_FORMAT`/`encode_to_bytes`/`step_down_resize`/`compress_image`(반환 dict `ok/out_path/size_kb/error`) 이름·시그니처가 Task 1→2→3 전체에서 일치.
