# 이미지 다이어트 데스크톱 툴킷 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 우클릭으로 열리는 탭 창(압축/Base64/SVG/PDF)을 만들고, 복수 선택을 한 창에서 처리하며, 압축은 파일별·전체 절감량을 보여준다.

**Architecture:** 로직(tkinter 미의존, Pillow/표준라이브러리)과 UI(tkinter)를 분리한다. 로직 모듈 `b64tool`·`pdftool`·`svgtool`·`singleinstance`는 WSL pytest로 검증하고, 공용 위젯 `widgets.py`와 탭별 뷰·탭 창은 Windows에서 위젯 트리 빌드 스모크로 검증한다. 진입점 파일명 `compress_gui.pyw`는 유지해 재설치가 필요 없다.

**Tech Stack:** Python 3.x, Pillow, tkinter(표준), 표준 socket, pytest.

## Global Constraints

- 의존성은 **Python + Pillow만**. 추가 pip 패키지 금지(vtracer/numpy/cairosvg 등 사용 안 함).
- 로직 모듈(`b64tool`,`pdftool`,`svgtool`,`singleinstance`)은 **`import tkinter` 금지** — WSL에서 pytest 가능해야 함.
- 신규 파일은 `shell/` 아래. 압축 엔진 `shell/compress.py`는 **불변**.
- 진입점 파일명은 `shell/compress_gui.pyw` **유지**(레지스트리 명령 불변 → 재설치 불필요).
- 색: 틸 팔레트(라이트 accent `#0d9488` / 다크 `#2dd4bf`), 다크모드 자동(`AppsUseLightTheme`), 창 중앙 배치, resizable False.
- 결과 파일명은 원본과 같은 폴더에 숫자만 붙임(`compress.numbered_output_path` 규칙 재사용). 원본 미변경.
- 복수 선택 취합 포트 `51737`, 취합 창 `0.8`초, 루프백 `127.0.0.1`만(방화벽·관리자 불필요).
- SVG 슬라이더 매핑(웹앱과 동일): detail(1–5)→workRes `[128,192,320,448,640]`, simplify(0–4)→tol `[0.3,0.6,1.0,1.6,2.4]`, noise(0–4)→minArea `[0,3,9,24,60]`, colors 2–16, gap 0–4(step .5), smooth bool.
- SVG 프리셋: `logo{colors:4,detail:5,simplify:2,noise:3,smooth:True}`, `illust{8,4,1,2,True}`, `photo{16,5,1,1,True}`.
- 테스트는 WSL `python3`(Pillow 12). GUI는 Windows Python(`C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\python.exe`)로 스모크.

> **Windows 스모크 패턴**(뷰/창 태스크 공통): 창을 숨긴 채 위젯 트리를 조립해 tkinter API 오류를 잡는다.
> ```
> cd "/mnt/c/dev/2026 soma/downsizing img/shell"
> # _smoke.py 작성 후:
> cmd.exe /c "C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\python.exe _smoke.py"
> ```
> `_smoke.py`는 `root=tk.Tk(); root.withdraw()` 후 대상 위젯/뷰를 생성하고 `root.update()`; 성공 시 `SMOKE_OK` 출력, 끝나면 `rm -f _smoke.py`.

---

### Task 1: Base64 도구 로직 (`b64tool.py`)

**Files:**
- Create: `shell/b64tool.py`
- Test: `shell/test_b64tool.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `to_data_uri(path: str) -> str` — `data:image/<mime>;base64,....`
  - `variants(path: str) -> dict` — `{"datauri": str, "imgtag": str, "css": str}`
  - `decode_to_file(text: str, out_path: str) -> str` — data URI 또는 순수 base64를 이미지 파일로 저장, 저장 경로 반환. 형식은 data URI 헤더 또는 매직바이트로 결정.

- [ ] **Step 1: 실패하는 테스트 작성**

`shell/test_b64tool.py`:

```python
import base64
import os
from PIL import Image
import b64tool


def _png(path):
    Image.new("RGB", (8, 8), (200, 30, 30)).save(path, "PNG")


def test_to_data_uri_png(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    uri = b64tool.to_data_uri(str(p))
    assert uri.startswith("data:image/png;base64,")
    head, b64 = uri.split(",", 1)
    assert base64.b64decode(b64)[:8] == b"\x89PNG\r\n\x1a\n"


def test_variants_shapes(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    v = b64tool.variants(str(p))
    assert v["datauri"].startswith("data:image/png;base64,")
    assert v["imgtag"].startswith("<img src=\"data:image/png;base64,") and v["imgtag"].endswith("\">")
    assert v["css"].startswith("background-image:url(\"data:image/png;base64,") and v["css"].endswith("\")")


def test_decode_data_uri_roundtrip(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    uri = b64tool.to_data_uri(str(p))
    out = b64tool.decode_to_file(uri, str(tmp_path / "out"))
    assert out.endswith(".png")
    with Image.open(out) as im:
        assert im.size == (8, 8)


def test_decode_raw_base64_detects_png(tmp_path):
    p = tmp_path / "a.png"; _png(str(p))
    raw = base64.b64encode(open(p, "rb").read()).decode()
    out = b64tool.decode_to_file(raw, str(tmp_path / "out"))
    assert out.endswith(".png")


def test_decode_bad_input_raises(tmp_path):
    try:
        b64tool.decode_to_file("not base64 @@@", str(tmp_path / "out"))
        assert False, "expected error"
    except ValueError:
        pass
```

- [ ] **Step 2: 실패 확인**

Run: `cd "shell" && python3 -m pytest test_b64tool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'b64tool'`.

- [ ] **Step 3: 구현**

`shell/b64tool.py`:

```python
"""Base64 인코딩/디코딩 (tkinter 미의존)."""
import base64
import binascii
import os

_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"RIFF", "webp", "image/webp"),   # RIFF....WEBP
    (b"BM", "bmp", "image/bmp"),
    (b"GIF8", "gif", "image/gif"),
]


def _sniff(data: bytes):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    for sig, ext, mime in _MAGIC:
        if data.startswith(sig):
            return ext, mime
    return "png", "image/png"


def to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    _ext, mime = _sniff(data)
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))


def variants(path: str) -> dict:
    uri = to_data_uri(path)
    return {
        "datauri": uri,
        "imgtag": '<img src="%s">' % uri,
        "css": 'background-image:url("%s")' % uri,
    }


def decode_to_file(text: str, out_path: str) -> str:
    s = (text or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma < 0:
            raise ValueError("잘못된 Data URI 입니다.")
        s = s[comma + 1:]
    s = "".join(s.split())
    try:
        data = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Base64 문자열을 해석할 수 없습니다.")
    if not data:
        raise ValueError("빈 데이터입니다.")
    ext, _mime = _sniff(data)
    root, _ = os.path.splitext(out_path)
    final = root + "." + ext
    with open(final, "wb") as f:
        f.write(data)
    return final
```

- [ ] **Step 4: 통과 확인**

Run: `cd "shell" && python3 -m pytest test_b64tool.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/b64tool.py shell/test_b64tool.py
git commit -m "feat(shell): Base64 인코딩/디코딩 로직"
```

---

### Task 2: PDF 만들기 로직 (`pdftool.py`)

**Files:**
- Create: `shell/pdftool.py`
- Test: `shell/test_pdftool.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `images_to_pdf(paths: list[str], out_path: str, fit: str = "image") -> str` — 여러 이미지를 순서대로 한 PDF로 저장. `fit="image"`면 각 페이지=이미지 크기, `fit="a4"`면 A4(595×842pt)에 비율 유지로 맞춤(흰 배경). 저장 경로 반환. 빈 목록이면 ValueError.

- [ ] **Step 1: 실패하는 테스트 작성**

`shell/test_pdftool.py`:

```python
from PIL import Image
import pdftool


def _img(path, size, color):
    Image.new("RGB", size, color).save(path)


def test_combine_pages(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (100, 80), (255, 0, 0))
    b = tmp_path / "b.png"; _img(str(b), (60, 120), (0, 128, 0))
    out = pdftool.images_to_pdf([str(a), str(b)], str(tmp_path / "doc.pdf"))
    assert out.endswith(".pdf")
    with open(out, "rb") as f:
        head = f.read(5)
    assert head == b"%PDF-"


def test_a4_fit_runs(tmp_path):
    a = tmp_path / "a.png"; _img(str(a), (2000, 100), (10, 10, 200))
    out = pdftool.images_to_pdf([str(a)], str(tmp_path / "d.pdf"), fit="a4")
    with Image.open(out) as im:
        assert im.size == (595, 842)


def test_empty_raises(tmp_path):
    try:
        pdftool.images_to_pdf([], str(tmp_path / "x.pdf"))
        assert False
    except ValueError:
        pass
```

- [ ] **Step 2: 실패 확인**

Run: `cd "shell" && python3 -m pytest test_pdftool.py -v`
Expected: FAIL — 모듈 없음.

- [ ] **Step 3: 구현**

`shell/pdftool.py`:

```python
"""이미지 여러 장 -> 한 PDF (tkinter 미의존)."""
import os
from PIL import Image

A4 = (595, 842)  # 72dpi 포인트


def _load_rgb(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def _fit_a4(im):
    page = Image.new("RGB", A4, (255, 255, 255))
    scale = min(A4[0] / im.width, A4[1] / im.height)
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    resized = im.resize((w, h), Image.LANCZOS)
    page.paste(resized, ((A4[0] - w) // 2, (A4[1] - h) // 2))
    return page


def images_to_pdf(paths, out_path, fit="image"):
    if not paths:
        raise ValueError("이미지가 없습니다.")
    pages = []
    for p in paths:
        im = _load_rgb(p)
        pages.append(_fit_a4(im) if fit == "a4" else im)
    root, _ = os.path.splitext(out_path)
    final = root + ".pdf"
    pages[0].save(final, "PDF", save_all=True, append_images=pages[1:])
    return final
```

- [ ] **Step 4: 통과 확인**

Run: `cd "shell" && python3 -m pytest test_pdftool.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/pdftool.py shell/test_pdftool.py
git commit -m "feat(shell): 이미지->PDF 로직"
```

---

### Task 3: 복수 선택 취합 (`singleinstance.py`)

**Files:**
- Create: `shell/singleinstance.py`
- Test: `shell/test_singleinstance.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `coalesce(argv_files: list[str], port: int = 51737, window: float = 0.8) -> list | None` — 첫 인스턴스면 형제들이 보낸 경로를 취합해 리스트 반환. 형제 인스턴스면 자기 경로 전송 후 `None` 반환.

- [ ] **Step 1: 실패하는 테스트 작성**

`shell/test_singleinstance.py`:

```python
import threading
import time
import singleinstance as si

PORT = 51999  # 테스트 전용 포트


def test_server_collects_sibling_files():
    result = {}

    def server():
        result["files"] = si.coalesce(["/a.jpg"], port=PORT, window=0.6)

    t = threading.Thread(target=server)
    t.start()
    time.sleep(0.15)  # 서버가 바인드할 시간
    # 형제 두 개
    assert si.coalesce(["/b.jpg"], port=PORT, window=0.6) is None
    assert si.coalesce(["/c.jpg"], port=PORT, window=0.6) is None
    t.join(2.0)
    assert set(result["files"]) == {"/a.jpg", "/b.jpg", "/c.jpg"}


def test_no_server_returns_own_when_connect_fails():
    # 아무도 안 여는 포트로 connect 실패 -> 폴백(자기 파일)
    files = si.coalesce(["/solo.jpg"], port=51998, window=0.2)
    # 서버로 바인드 성공하면 리스트, 형제면 None. 단독 실행이므로 리스트여야 함.
    assert files == ["/solo.jpg"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd "shell" && python3 -m pytest test_singleinstance.py -v`
Expected: FAIL — 모듈 없음.

- [ ] **Step 3: 구현**

`shell/singleinstance.py`:

```python
"""복수 선택 취합: 첫 인스턴스가 서버가 되어 형제들의 파일 경로를 모은다.
tkinter 미의존, 루프백 소켓만 사용."""
import socket
import threading
import time

_MAGIC = b"IMGDIET1\n"


def coalesce(argv_files, port=51737, window=0.8):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(16)
    except OSError:
        srv.close()
        return _send_to_server(argv_files, port)

    # 서버: 형제 연결을 window초 동안 수신
    collected = list(argv_files)
    deadline = [time.time() + window]
    lock = threading.Lock()
    stop = threading.Event()

    def accept_loop():
        srv.settimeout(0.1)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(0.5)
                data = b""
                while b"\n" not in data[len(_MAGIC):] or not data.startswith(_MAGIC):
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 65536:
                        break
                if data.startswith(_MAGIC):
                    payload = data[len(_MAGIC):].decode("utf-8", "replace")
                    with lock:
                        for line in payload.splitlines():
                            if line:
                                collected.append(line)
                        deadline[0] = time.time() + 0.25  # 새 파일 오면 조금 연장
            finally:
                conn.close()

    th = threading.Thread(target=accept_loop, daemon=True)
    th.start()
    while time.time() < deadline[0]:
        time.sleep(0.05)
    stop.set()
    srv.close()
    th.join(1.0)
    with lock:
        return list(collected)


def _send_to_server(argv_files, port):
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.settimeout(1.0)
        c.connect(("127.0.0.1", port))
        payload = _MAGIC + ("\n".join(argv_files) + "\n").encode("utf-8")
        c.sendall(payload)
        c.close()
        return None
    except OSError:
        return list(argv_files)  # 우리 서버가 아니면 폴백: 단독 창
```

- [ ] **Step 4: 통과 확인**

Run: `cd "shell" && python3 -m pytest test_singleinstance.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/singleinstance.py shell/test_singleinstance.py
git commit -m "feat(shell): 복수 선택 단일 인스턴스 취합"
```

---

### Task 4: SVG 벡터화 (`svgtool.py`) — 웹앱 알고리즘 충실 포팅

**Files:**
- Create: `shell/svgtool.py`
- Test: `shell/test_svgtool.py`
- 참조: `index.html` 2949–3320행(quantizePalette/traceLoops/vectorizeToSvg/buildSvgFromEntries), 3505–3560행(dpClosed/dpSimplify)

**Interfaces:**
- Consumes: Pillow `Image`
- Produces:
  - `RES = [128,192,320,448,640]`, `TOL = [0.3,0.6,1.0,1.6,2.4]`, `AREA = [0,3,9,24,60]`
  - `PRESETS = {"logo":{...}, "illust":{...}, "photo":{...}}` (Global Constraints 값)
  - `default_opts() -> dict` — `{"colors":6,"detail":3,"simplify":2,"noise":2,"gap":1.0,"smooth":True}`
  - `opts_from_controls(colors, detail, simplify, noise, gap, smooth) -> dict` — 슬라이더값 → `{"colors","workRes","tol","minArea","gap","smooth"}` (RES/TOL/AREA 매핑)
  - `vectorize(img: Image, opts: dict) -> str` — SVG 문자열. `opts`는 `opts_from_controls` 결과 형태.

- [ ] **Step 1: 실패하는 테스트 작성**

`shell/test_svgtool.py`:

```python
from PIL import Image, ImageDraw
import svgtool


def _shape():
    im = Image.new("RGB", (120, 120), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 100, 100), fill=(220, 30, 30))
    d.rectangle((40, 40, 80, 80), fill=(20, 60, 200))
    return im


def test_opts_mapping():
    o = svgtool.opts_from_controls(colors=4, detail=5, simplify=2, noise=3, gap=1.0, smooth=True)
    assert o["colors"] == 4
    assert o["workRes"] == 640      # detail 5 -> RES[4]
    assert o["tol"] == 1.0          # simplify 2 -> TOL[2]
    assert o["minArea"] == 24       # noise 3 -> AREA[3]


def test_presets_exist():
    assert svgtool.PRESETS["logo"]["colors"] == 4
    assert svgtool.PRESETS["photo"]["detail"] == 5


def test_vectorize_produces_svg():
    o = svgtool.opts_from_controls(6, 3, 2, 2, 1.0, True)
    svg = svgtool.vectorize(_shape(), o)
    assert svg.lstrip().startswith("<svg")
    assert "<path" in svg
    assert svg.rstrip().endswith("</svg>")


def test_fewer_colors_is_valid():
    o = svgtool.opts_from_controls(2, 2, 2, 2, 1.0, True)
    svg = svgtool.vectorize(_shape(), o)
    assert "<svg" in svg and "</svg>" in svg
```

- [ ] **Step 2: 실패 확인**

Run: `cd "shell" && python3 -m pytest test_svgtool.py -v`
Expected: FAIL — 모듈 없음.

- [ ] **Step 3: 구현 — index.html 알고리즘 포팅**

`index.html`의 아래 함수들을 **동작 그대로** Python(Pillow 픽셀 접근, 순수 Python)로 옮긴다:

- `quantizePalette(data, n)` (2949–3007): median-cut 색 양자화. Pillow는 `img.quantize(colors=n, method=Image.MEDIANCUT)`로 대체 가능하나, 결과 인덱스맵+팔레트를 web과 맞추려면 동일 로직 포팅 권장. **간결·동등성 위해 `img.convert("RGB").quantize(colors=n, method=Image.Quantize.MEDIANCUT)` 사용 허용** — 인덱스맵(`list(pal_img.getdata())`)과 팔레트(`pal_img.getpalette()`)를 얻는다.
- `traceLoops(mask, w, h)` (3008–3172): 색별 이진 마스크의 경계를 Eulerian 루프로 추적(fill-rule evenodd). 이 부분은 라이브러리 대체가 없으므로 **그대로 포팅**한다(무어 경계추적/에지 루프 분해).
- `dpSimplify`/`dpClosed` (3505–3560): Douglas–Peucker. 그대로 포팅.
- `vectorizeToSvg(source, opts)` (3173–3284): 위를 엮어 색별 루프→단순화→(smooth 시) 이차 베지어. 그대로 포팅. `opts` 키(`colors,workRes,tol,minArea,gap,smooth`) 동일.
- `buildSvgFromEntries(...)` (3285–3324): 경로 문자열 조립 → 최종 `<svg ...>...</svg>`. 그대로 포팅.

전처리(웹앱과 동일): 입력을 `workRes`(긴 변 기준)로 축소 후 벡터화. `minArea` 미만 루프 버림. `gap`은 같은 색 stroke 폭으로 도형 사이 빈틈 메움(`buildSvgFromEntries`의 strokeW).

모듈 구조:

```python
"""이미지 -> SVG 벡터화. index.html 2949-3320,3505-3560 포팅. Pillow만 사용."""
from PIL import Image

RES = [128, 192, 320, 448, 640]
TOL = [0.3, 0.6, 1.0, 1.6, 2.4]
AREA = [0, 3, 9, 24, 60]

PRESETS = {
    "logo":   {"colors": 4,  "detail": 5, "simplify": 2, "noise": 3, "smooth": True},
    "illust": {"colors": 8,  "detail": 4, "simplify": 1, "noise": 2, "smooth": True},
    "photo":  {"colors": 16, "detail": 5, "simplify": 1, "noise": 1, "smooth": True},
}


def default_opts():
    return {"colors": 6, "detail": 3, "simplify": 2, "noise": 2, "gap": 1.0, "smooth": True}


def opts_from_controls(colors, detail, simplify, noise, gap, smooth):
    return {
        "colors": int(colors),
        "workRes": RES[int(detail) - 1],
        "tol": TOL[int(simplify)],
        "minArea": AREA[int(noise)],
        "gap": float(gap),
        "smooth": bool(smooth),
    }

# _quantize(img,n) -> (indices:list[int], palette:list[(r,g,b)], w, h)
# _trace_loops(mask,w,h) -> list[list[(x,y)]]      (traceLoops 포팅)
# _dp_closed(pts,tol) -> list[(x,y)]               (dpClosed 포팅)
# _loops_to_path(loops, smooth) -> str             (path d 문자열)
# vectorize(img, opts) -> str                       (vectorizeToSvg+buildSvgFromEntries)
```

`vectorize`는 반드시 `"<svg"`로 시작하고 `"</svg>"`로 끝나며 색상 그룹마다 `<path fill=... d=.../>`를 포함해야 한다(테스트 기준).

> **포팅 지침:** 먼저 `index.html`의 해당 줄들을 읽고, 함수별로 1:1 대응해 옮긴다. JS의 `Uint8Array`/`Int32Array`는 Python `list`/`bytearray`로, `ctx.getImageData`는 `img.load()` 픽셀 접근으로 바꾼다. 좌표/스케일 계산은 값 그대로 유지한다. 성능을 위해 전처리 축소(`workRes`)를 반드시 먼저 적용한다.

- [ ] **Step 4: 통과 확인**

Run: `cd "shell" && python3 -m pytest test_svgtool.py -v`
Expected: PASS (4 passed). 결과 SVG가 유효 태그 구조를 갖는지 확인.

- [ ] **Step 5: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/svgtool.py shell/test_svgtool.py
git commit -m "feat(shell): 이미지->SVG 벡터화 (웹앱 알고리즘 포팅)"
```

---

### Task 5: 공용 위젯 모듈 (`widgets.py`)

현재 `compress_gui.pyw`에 있는 공용 UI 요소를 `widgets.py`로 추출한다(뷰들이 공유).

**Files:**
- Create: `shell/widgets.py`
- Modify: `shell/compress_gui.pyw`(임시로 `from widgets import *` 참조하도록 정리는 Task 10에서 마무리)

**Interfaces:**
- Produces (현재 compress_gui.pyw의 동일 구현을 이동, 이름만 공개형으로):
  - `round_rect(cv, x1, y1, x2, y2, r, **kw)`
  - `is_dark() -> bool`, `palette(dark) -> dict`, `human(n) -> str`, `elide(name, keep=30) -> str`
  - `chip(parent, text, fg, bg, cardbg) -> Canvas`
  - `class RoundButton(tk.Canvas)`: `(parent, text, command, pal, kind="primary", w=120, h=40)`
  - `class Segmented(tk.Canvas)`: `(parent, options, value, pal, w, h)` — `options`는 `[(label,value),...]`, 선택값 `.value`
  - `class Bar(tk.Canvas)`: `(parent, pal, w, h)` + `.set(frac)`

- [ ] **Step 1: widgets.py 작성**

현재 `shell/compress_gui.pyw`의 `_round_rect`,`_chip`,`RoundButton`,`Segmented`,`Bar`,`_is_dark`,`_palette`,`_human`,`_elide`를 그대로 `shell/widgets.py`로 옮기고 공개 이름으로 노출한다. 파일 상단:

```python
"""공용 Tkinter 위젯·팔레트."""
import tkinter as tk

# (compress_gui.pyw 에서 _round_rect -> round_rect, _palette -> palette,
#  _is_dark -> is_dark, _human -> human, _elide -> elide, _chip -> chip 로
#  이름만 바꿔 그대로 이동. RoundButton/Segmented/Bar 클래스는 동일.)
```

`palette(dark)`의 키·색값은 현재 `_palette`와 100% 동일하게 유지한다(틸 팔레트).

- [ ] **Step 2: Windows 스모크**

`_smoke.py`에서 `import widgets`, `root=tk.Tk();root.withdraw()`, `p=widgets.palette(False)`, `widgets.RoundButton(root,"x",lambda:None,p)`, `widgets.Segmented(root,[("자동","auto"),("WebP","webp")],"auto",p,w=200)`, `widgets.Bar(root,p,w=200).set(0.5)`, `widgets.chip(root,"✓ 48KB",p["ok"],p["ok_soft"],p["card"])`, `root.update()`, print `SMOKE_OK`.

Run(스모크 패턴): Expected `SMOKE_OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/widgets.py
git commit -m "feat(shell): 공용 위젯 모듈 추출"
```

---

### Task 6: 압축 탭 뷰 (`view_compress.py`)

현재 압축 UI를 뷰 클래스로 옮기고, **파일별 원본→결과** 표시를 추가한다.

**Files:**
- Create: `shell/view_compress.py`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `widgets`(RoundButton,Segmented,Bar,chip,palette,human,elide,round_rect), `compress.compress_image`
- Produces: `class CompressView(tk.Frame)`: `(parent, pal, files, recenter)` — `recenter`는 창 재중앙 콜백. 자체적으로 설정→진행→요약 화면을 관리.

- [ ] **Step 1: view_compress.py 작성**

현재 `compress_gui.pyw`의 `App`이 하던 압축 UI(설정: 목표용량+세그먼트+[압축], 진행: Bar+결과행+요약)를 `CompressView(tk.Frame)`로 옮긴다. 위젯은 `widgets.py`에서 import. **변경점**: 결과 행에 원본→결과 크기 표시.

```python
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
```

- [ ] **Step 2: Windows 스모크**

`_smoke.py`: 숨긴 root에 `CompressView(root, widgets.palette(d), ["C:/x/a.jpg","C:/x/b.png"], lambda: None)` 생성(라이트+다크), `.pack()`, `root.update()`; `_show_progress`·`_row(...)`·`_finish(2,1258291,188743)` 호출 후 `root.update()`; `SMOKE_OK`.

Run(스모크 패턴): Expected `SMOKE_OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/view_compress.py
git commit -m "feat(shell): 압축 탭 뷰 (+파일별 원본->결과)"
```

---

### Task 7: Base64 탭 뷰 (`view_base64.py`)

**Files:**
- Create: `shell/view_base64.py`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `widgets`, `b64tool`
- Produces: `class Base64View(tk.Frame)`: `(parent, pal, files, recenter)`

- [ ] **Step 1: view_base64.py 작성**

```python
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
```

- [ ] **Step 2: Windows 스모크**

`_smoke.py`: 실제 작은 png를 tmp에 만들고 `Base64View(root, palette(d), [png], lambda:None)` 생성(라이트+다크), `.pack()`, `root.update()`; `SMOKE_OK`.

Run(스모크 패턴): Expected `SMOKE_OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/view_base64.py
git commit -m "feat(shell): Base64 탭 뷰"
```

---

### Task 8: PDF 탭 뷰 (`view_pdf.py`)

**Files:**
- Create: `shell/view_pdf.py`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `widgets`, `pdftool`
- Produces: `class PdfView(tk.Frame)`: `(parent, pal, files, recenter)`

- [ ] **Step 1: view_pdf.py 작성**

```python
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
```

- [ ] **Step 2: Windows 스모크**

`_smoke.py`: `PdfView(root, palette(d), ["C:/x/a.jpg","C:/x/b.png"], lambda:None)`(라이트+다크), `.pack()`, `root.update()`; `SMOKE_OK`.

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/view_pdf.py
git commit -m "feat(shell): PDF 탭 뷰"
```

---

### Task 9: SVG 탭 뷰 (`view_svg.py`)

**Files:**
- Create: `shell/view_svg.py`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `widgets`, `svgtool`, `compress.numbered_output_path`, Pillow
- Produces: `class SvgView(tk.Frame)`: `(parent, pal, files, recenter)`

- [ ] **Step 1: view_svg.py 작성**

파라미터 슬라이더 5개 + 프리셋 칩 + [변환] + [결과 열기]. 변환은 `svgtool.opts_from_controls(...)`→`svgtool.vectorize(img,opts)`→원본 옆 `name1.svg` 저장(`compress.numbered_output_path(src,".svg")`).

```python
"""SVG 탭: 파라미터 조절 후 이미지->SVG 변환·저장."""
import os
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import compress
import svgtool
import widgets as W

INNER = 360
SLIDERS = [
    ("색상 수", "colors", 2, 16, 6),
    ("추적 정밀도", "detail", 1, 5, 3),
    ("외곽선 단순화", "simplify", 0, 4, 2),
    ("잡티 제거", "noise", 0, 4, 2),
    ("빈틈 메우기", "gap", 0, 4, 2),
]


class SvgView(tk.Frame):
    def __init__(self, parent, pal, files, recenter):
        super().__init__(parent, bg=pal["card"])
        self.pal, self.files, self.recenter = pal, files, recenter
        self._last = None
        p = pal
        self.vars = {}
        pr = tk.Frame(self, bg=p["card"]); pr.pack(fill="x", pady=(0, 8))
        tk.Label(pr, text="프리셋", bg=p["card"], fg=p["sub"], font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        for key, label in (("logo", "로고"), ("illust", "일러스트"), ("photo", "사진")):
            W.RoundButton(pr, label, (lambda k=key: self._preset(k)), p, "ghost", w=74, h=30).pack(side="left", padx=3)
        grid = tk.Frame(self, bg=p["card"]); grid.pack(fill="x")
        for i, (label, key, lo, hi, dv) in enumerate(SLIDERS):
            tk.Label(grid, text=label, bg=p["card"], fg=p["sub"], font=("Segoe UI", 9),
                     anchor="w").grid(row=i, column=0, sticky="w", pady=3)
            v = tk.DoubleVar(value=dv) if key == "gap" else tk.IntVar(value=dv)
            self.vars[key] = v
            res = "0.5" if key == "gap" else 1
            tk.Scale(grid, from_=lo, to=hi, resolution=res, orient="horizontal",
                     variable=v, length=INNER - 96, bg=p["card"], fg=p["ink"],
                     troughcolor=p["field"], highlightthickness=0, bd=0).grid(row=i, column=1, sticky="w")
        self.smooth = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="곡선 스무딩", variable=self.smooth, bg=p["card"], fg=p["sub"],
                       selectcolor=p["field"], activebackground=p["card"]).pack(anchor="w", pady=(4, 8))
        b = tk.Frame(self, bg=p["card"]); b.pack(fill="x")
        W.RoundButton(b, "SVG 변환", self._convert, p, "primary", w=INNER - 110, h=40).pack(side="left")
        self.openbtn = W.RoundButton(b, "결과 열기", self._open, p, "ghost", w=102, h=40)
        self.openbtn.pack(side="right")

    def _preset(self, key):
        pr = svgtool.PRESETS[key]
        for k in ("colors", "detail", "simplify", "noise"):
            self.vars[k].set(pr[k])
        self.smooth.set(pr["smooth"])

    def _convert(self):
        if not self.files:
            return
        opts = svgtool.opts_from_controls(
            self.vars["colors"].get(), self.vars["detail"].get(),
            self.vars["simplify"].get(), self.vars["noise"].get(),
            self.vars["gap"].get(), self.smooth.get())
        src = self.files[0]
        threading.Thread(target=self._work, args=(src, opts), daemon=True).start()

    def _work(self, src, opts):
        try:
            img = Image.open(src).convert("RGB")
            svg = svgtool.vectorize(img, opts)
            out = compress.numbered_output_path(src, ".svg")
            with open(out, "w", encoding="utf-8") as f:
                f.write(svg)
            self._last = out
            self.after(0, lambda: messagebox.showinfo("이미지 다이어트", "저장됨: %s" % out))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("이미지 다이어트", str(e)))

    def _open(self):
        if self._last and os.path.exists(self._last):
            try:
                os.startfile(self._last)  # noqa: WPS (Windows 전용)
            except Exception:
                pass
```

- [ ] **Step 2: Windows 스모크**

`_smoke.py`: `SvgView(root, palette(d), ["C:/x/a.png"], lambda:None)`(라이트+다크), `.pack()`, `root.update()`, `_preset("logo")` 호출; `SMOKE_OK`. (실제 변환은 수동)

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/view_svg.py
git commit -m "feat(shell): SVG 탭 뷰"
```

---

### Task 10: 탭 창 + 취합 진입점 (`compress_gui.pyw` 재작성)

기존 단일 압축 창을 **탭 창**으로 바꾸고, 진입 시 복수선택을 취합한다.

**Files:**
- Rewrite: `shell/compress_gui.pyw`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `singleinstance.coalesce`, `widgets`(palette,is_dark,Segmented,round_rect), `view_compress.CompressView`, `view_base64.Base64View`, `view_svg.SvgView`, `view_pdf.PdfView`
- Produces: `main()` 진입점

- [ ] **Step 1: compress_gui.pyw 재작성**

```python
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
```

- [ ] **Step 2: Windows 통합 스모크**

`_smoke.py`: `SourceFileLoader`로 compress_gui.pyw 로드, 숨긴 root에 `Toolkit(root, [tmp_png, tmp_png2])` 생성, `root.update()`, 각 탭 `_show(0.._3)` 호출 후 `root.update()`; `SMOKE_OK`. (라이트+다크)

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/compress_gui.pyw
git commit -m "feat(shell): 탭 창 + 복수선택 취합 진입점"
```

---

### Task 11: 문서 + 전체 회귀

**Files:**
- Modify: `shell/README.md`
- Modify: `README.md`(루트, 필요 시)

- [ ] **Step 1: shell/README.md 갱신**

`shell/README.md`의 사용 섹션에 4개 탭(압축/Base64/SVG/PDF)과 복수선택 한 창 처리, 구성 표에 신규 파일(`b64tool.py`,`pdftool.py`,`svgtool.py`,`singleinstance.py`,`widgets.py`,`view_*.py`)을 반영한다. (구체 문구는 기존 톤에 맞춰 작성)

- [ ] **Step 2: 전체 테스트 회귀**

Run:
```bash
cd "/mnt/c/dev/2026 soma/downsizing img/shell" && python3 -m pytest -q && rm -rf __pycache__
```
Expected: 모든 로직 테스트 통과(`test_compress`,`test_b64tool`,`test_pdftool`,`test_svgtool`,`test_singleinstance`).

- [ ] **Step 3: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/README.md README.md
git commit -m "docs(shell): 툴킷 4개 탭 사용 안내"
```

---

## 수동 검증 (사용자, Windows)

install.bat은 이미 `compress_gui.pyw`를 가리키므로 **재설치 불필요**. 이미지 우클릭 → 탭 창.
1. **복수 선택** 우클릭 → **한 창**에 "파일 N개", 압축 탭에서 일괄 처리·파일별 `원본→결과`·총 절감.
2. **Base64** 탭: Data URI/`<img>`/CSS 복사, 붙여넣어 이미지로 저장.
3. **SVG** 탭: 프리셋·슬라이더 조절 → 변환 → `name1.svg` 저장 → 결과 열기.
4. **PDF** 탭: 여러 장 → 한 PDF(이미지 크기/A4).

## Self-Review 결과

- **Spec coverage:** 4개 탭(T6–9)·탭 창(T10)·복수선택 취합(T3,T10)·파일별+전체 절감(T6)·SVG 충실 포팅(T4, index.html 참조)·모듈 분리/테스트가능(T1–4)·진입점 유지(T10)·문서(T11) 모두 커버. SVG 미리보기 없음·A4옵션·PDF합치기 기본 반영.
- **Placeholder scan:** 로직·뷰·창 코드 완전 제공. SVG 알고리즘은 "포팅" 특성상 원본 줄 범위+인터페이스+테스트로 명시(플레이스홀더 아님, 기존 소스가 사양).
- **Type/이름 일관성:** `widgets`(round_rect/palette/human/elide/chip/RoundButton/Segmented/Bar), 뷰 생성자 `(parent, pal, files, recenter)`, `svgtool.opts_from_controls/vectorize/PRESETS`, `singleinstance.coalesce`, `b64tool.to_data_uri/variants/decode_to_file`, `pdftool.images_to_pdf`가 태스크 전반에서 일치. 진입점 `compress_gui.pyw` 유지.
