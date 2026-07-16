# Base64 탭 — 글자수 + 압축하기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 데스크톱 Base64 탭에 웹앱과 동일한 **글자수 표시**와 **압축해서 변환**(1920px 상한 + 품질 슬라이더)을 넣는다.

**Architecture:** 로직은 `b64tool.py`에 `to_data_uri_compressed`를 추가하고 축소·인코딩은 기존 `compress.py`의 `step_down_resize`/`encode_to_bytes`를 재사용(tkinter 미의존 → WSL pytest). UI는 `view_base64.py`에 체크박스·품질 슬라이더·글자수·통계 줄을 추가하고, 재인코딩은 백그라운드 스레드 + 기존 `_post`/`winfo_exists` 가드로 처리한다.

**Tech Stack:** Python, Pillow, tkinter, pytest.

## Global Constraints

웹앱(`index.html` 2411–2475행)의 동작을 그대로 맞춘다:

- **압축해서 변환 OFF**(기본): 원본 파일 바이트를 그대로 Data URI로 (`to_data_uri` 기존 동작).
- **ON**: 긴 변 기준 `s = min(1, 1920/max(w,h))` 로 축소 → **WebP**로 재인코딩(품질 슬라이더 값) → Data URI.
- 품질 슬라이더: **0.4 ~ 0.95, step 0.01, 기본 0.8**, 라벨 "압축 품질 80%". 체크 시에만 표시. 값 변경 시 재인코딩.
- 글자수 표시 형식: `12,345자` (천 단위 구분). 인코딩 결과 textarea + 디코딩 입력 textarea 양쪽.
- 통계 줄 형식: `원본 <크기>[ → 압축 <크기> (<w>×<h>)] → 문자열 <크기> (+N%)`, `growth = round(len(datauri)/orig_size - 1) * 100`.
- 의존성은 **Python + Pillow만**. `b64tool.py`는 **`import tkinter` 금지**(WSL pytest 가능).
- 기존 동작 불변: 복사 버튼 3종(Data URI/`<img>`/CSS), 디코딩·저장, 원본 썸네일 미리보기, `to_data_uri`/`variants`/`decode_to_file` 시그니처.
- `ImageTk.PhotoImage`는 메인 스레드에서만(기존 규칙). 무거운 재인코딩은 백그라운드 스레드 → `_post`로 표시.
- 테스트: WSL `python3`(Pillow 12). GUI 스모크: Windows Python `C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\python.exe`(창 숨김 + 위젯 빌드, `SMOKE_OK`).

---

### Task 1: 압축 인코딩 로직 (`b64tool.to_data_uri_compressed`)

**Files:**
- Modify: `shell/b64tool.py`
- Test: `shell/test_b64tool.py`

**Interfaces:**
- Consumes: `compress.step_down_resize(img, scale)`, `compress.encode_to_bytes(img, fmt, quality)` (기존, 불변), Pillow.
- Produces:
  - `to_data_uri_compressed(path: str, max_side: int = 1920, quality: float = 0.8) -> dict`
    반환 키: `datauri`(str), `imgtag`(str), `css`(str), `orig_bytes`(int), `comp_bytes`(int), `w`(int), `h`(int).
    긴 변이 `max_side`를 넘으면 `step_down_resize`로 축소(안 넘으면 원본 크기 유지), WebP로 `encode_to_bytes(img, "webp", round(quality*100))` 인코딩, `data:image/webp;base64,...` 생성.

- [ ] **Step 1: 실패하는 테스트 작성**

`shell/test_b64tool.py`에 추가:

```python
def _big(path, size=(3000, 1500)):
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(0, size[1], 3):
        for x in range(0, size[0], 3):
            px[x, y] = ((x * 7) % 256, (y * 13) % 256, ((x + y) * 5) % 256)
    img.save(path, "PNG")


def test_compressed_caps_long_side_to_1920(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert max(r["w"], r["h"]) == 1920
    assert r["w"] == 1920 and r["h"] == 960          # 3000x1500 -> 2:1 유지
    assert r["datauri"].startswith("data:image/webp;base64,")


def test_compressed_is_smaller_than_raw(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    raw = b64tool.to_data_uri(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert len(r["datauri"]) < len(raw)               # 압축이 실제로 짧아야 함
    assert r["comp_bytes"] < r["orig_bytes"]


def test_compressed_small_image_not_upscaled(tmp_path):
    p = tmp_path / "small.png"
    Image.new("RGB", (100, 80), (10, 200, 120)).save(str(p))
    r = b64tool.to_data_uri_compressed(str(p), max_side=1920, quality=0.8)
    assert (r["w"], r["h"]) == (100, 80)              # 확대 금지


def test_compressed_quality_affects_size(tmp_path):
    p = tmp_path / "big.png"; _big(str(p))
    lo = b64tool.to_data_uri_compressed(str(p), quality=0.4)
    hi = b64tool.to_data_uri_compressed(str(p), quality=0.95)
    assert lo["comp_bytes"] < hi["comp_bytes"]


def test_compressed_variants_shapes(tmp_path):
    p = tmp_path / "small.png"
    Image.new("RGB", (60, 40), (200, 30, 30)).save(str(p))
    r = b64tool.to_data_uri_compressed(str(p))
    assert r["imgtag"].startswith('<img src="data:image/webp;base64,') and r["imgtag"].endswith('">')
    assert r["css"].startswith('background-image:url("data:image/webp;base64,') and r["css"].endswith('")')
```

- [ ] **Step 2: 실패 확인**

Run: `cd "shell" && python3 -m pytest test_b64tool.py -k compressed -v`
Expected: FAIL — `AttributeError: module 'b64tool' has no attribute 'to_data_uri_compressed'`.

- [ ] **Step 3: 구현**

`shell/b64tool.py`에 추가 (상단 import에 `import compress`, `from PIL import Image` 추가):

```python
import base64
import binascii
import os

from PIL import Image

import compress


def to_data_uri_compressed(path: str, max_side: int = 1920, quality: float = 0.8) -> dict:
    """웹앱의 '압축해서 변환'과 동일: 긴 변 max_side 로 축소 후 WebP 재인코딩 → Data URI."""
    orig_bytes = os.path.getsize(path)
    with Image.open(path) as opened:
        img = opened.convert("RGB") if opened.mode not in ("RGB", "RGBA") else opened.copy()
        w, h = img.size
        scale = min(1.0, float(max_side) / max(w, h)) if max(w, h) else 1.0
        if scale < 1.0:
            img = compress.step_down_resize(img, scale)
        data = compress.encode_to_bytes(img, "webp", int(round(quality * 100)))
        ow, oh = img.size
    uri = "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
    return {
        "datauri": uri,
        "imgtag": '<img src="%s">' % uri,
        "css": 'background-image:url("%s")' % uri,
        "orig_bytes": orig_bytes,
        "comp_bytes": len(data),
        "w": ow,
        "h": oh,
    }
```

기존 `to_data_uri`/`variants`/`decode_to_file`/`_sniff`/`_MAGIC`는 **그대로 둔다**.

- [ ] **Step 4: 통과 확인**

Run: `cd "shell" && python3 -m pytest test_b64tool.py -v`
Expected: PASS — 기존 5개 + 신규 5개 = 10 passed (기존 테스트 회귀 없음).

- [ ] **Step 5: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/b64tool.py shell/test_b64tool.py
git commit -m "feat(shell): b64tool 압축 변환(1920px+WebP 품질) 추가"
```

---

### Task 2: Base64 탭 UI — 글자수 · 압축 체크박스 · 품질 슬라이더 · 통계

**Files:**
- Modify: `shell/view_base64.py`
- Test: Windows 스모크

**Interfaces:**
- Consumes: `b64tool.to_data_uri_compressed`, `b64tool.variants`, `widgets`(RoundButton, Preview, human), 기존 `Base64View` 구조.
- Produces: `Base64View`에 압축 체크박스·품질 슬라이더·글자수 라벨 2개·통계 줄. 기존 복사/디코딩/썸네일 불변.

- [ ] **Step 1: view_base64.py 수정**

인코딩 섹션에 다음을 추가한다(기존 썸네일·Text·복사 버튼 유지):

```python
# 클래스 상단 헬퍼
def _chars(n):
    return "{:,}자".format(n)
```

`Base64View.__init__` 인코딩 섹션에:

```python
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
```

디코딩 섹션의 입력 Text 아래에 글자수:

```python
        self.incount = tk.Label(self, text=_chars(0), bg=p["card"], fg=p["sub"],
                                font=("Segoe UI", 9))
        self.incount.pack(anchor="e")
        self.dec.bind("<KeyRelease>", lambda e: self._upd_incount())
        self.dec.bind("<<Paste>>", lambda e: self.after(10, self._upd_incount))
```

메서드 추가:

```python
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
            self._post(lambda: self.stats.configure(text="변환 실패: %s" % str(e)[:40]))
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
```

`__init__`에서 `self._seq = 0`, `self._qpend = None` 초기화하고, 기존의 동기 인코딩 블록(`self._variants = b64tool.variants(...)` + `enc.insert`) 대신 마지막에 `self._reencode()`를 호출해 최초 인코딩을 수행한다. `_post`가 없으면 다른 뷰와 동일한 형태로 추가:

```python
    def _post(self, fn):
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except (tk.TclError, RuntimeError):
            pass
```

`import os`, `import threading`, `import tkinter as tk`, `import widgets as W`, `import b64tool` 확인.

- [ ] **Step 2: Windows 스모크**

`_smoke.py`:

```python
import sys, tempfile, os, time
from importlib.machinery import SourceFileLoader
BASE = r"C:\dev\2026 soma\downsizing img\shell"
sys.path.insert(0, BASE)
for m in ("widgets","compress","b64tool"):
    SourceFileLoader(m, BASE + "\\" + m + ".py").load_module()
import widgets as W
BV = SourceFileLoader("view_base64", BASE + r"\view_base64.py").load_module()
import tkinter as tk
from PIL import Image
png = os.path.join(tempfile.gettempdir(), "b64c.png")
Image.new("RGB", (2400, 1200), (30, 120, 200)).save(png)
for dark in (False, True):
    root = tk.Tk(); root.withdraw()
    v = BV.Base64View(root, W.palette(dark), [png], lambda: None)
    v.pack(); root.update()
    for _ in range(40): root.update(); time.sleep(0.02)     # 최초 인코딩 스레드
    assert "자" in v.outcount.cget("text"), v.outcount.cget("text")
    v.do_comp.set(True); v._reencode(); root.update()        # 압축 켜기
    for _ in range(60): root.update(); time.sleep(0.02)
    assert "압축" in v.stats.cget("text"), v.stats.cget("text")
    v.q.set(0.5); v._on_quality(); root.update()             # 품질 변경(디바운스)
    for _ in range(60): root.update(); time.sleep(0.02)
    v.dec.insert("1.0", "abc"); v._upd_incount(); root.update()
    assert v.incount.cget("text") == "3자", v.incount.cget("text")
    v.destroy(); root.update()
    v._post(lambda: None)
    root.destroy()
print("SMOKE_OK")
```

Run: `cd "shell" && cmd.exe /c "C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\python.exe _smoke.py" 2>&1 | tr -d '\r' | tail -10`
Expected: `SMOKE_OK` (트레이스백 없음). 이후 `rm -f shell/_smoke.py`.

- [ ] **Step 3: 회귀 + 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img/shell" && python3 -m pytest -q && rm -rf __pycache__ .pytest_cache
```
Expected: 37 passed (기존 32 + b64tool 신규 5).

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/view_base64.py
git commit -m "feat(shell): Base64 탭 글자수·압축해서 변환·품질 슬라이더"
```

---

### Task 3: 문서

**Files:**
- Modify: `shell/README.md`

- [ ] **Step 1: README 갱신**

사용 섹션의 **Base64** 줄에 글자수·압축 변환을 한 구절로 반영(기존 톤 유지). 예: "…원본 썸네일을 미리봅니다. 글자수를 표시하고, '압축해서 변환'을 켜면 최대 1920px·WebP로 줄여 더 짧은 Data URI를 만듭니다."

- [ ] **Step 2: 커밋**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/README.md
git commit -m "docs(shell): Base64 글자수·압축 변환 안내"
```

---

## 수동 검증 (사용자, Windows)

재설치 불필요. 이미지 우클릭 → Base64 탭:
1. 글자수가 `12,345자` 형식으로 보이는지.
2. **압축해서 변환** 체크 → 품질 슬라이더 나타남 → 통계에 `→ 압축 180KB (1920×1080)` 표시되고 **글자수가 줄어드는지**.
3. 품질을 낮추면 글자수가 더 줄어드는지.
4. 디코딩 입력창에 붙여넣으면 글자수가 갱신되는지.

## Self-Review 결과

- **Spec coverage:** 글자수(T2, 양쪽 textarea)·압축해서 변환 1920px+WebP(T1,T2)·품질 슬라이더 0.4~0.95/기본0.8(T2)·통계 줄 형식(T2)·재인코딩 트리거(T2)·기존 동작 불변(T1은 기존 함수 미변경, T2는 복사/디코딩 유지)·문서(T3) 커버.
- **Placeholder scan:** 로직·UI 코드 제공. GUI는 자동 테스트 불가라 스모크 명령·기대결과로 명시.
- **Type/이름 일관성:** `to_data_uri_compressed(path, max_side, quality) -> dict{datauri,imgtag,css,orig_bytes,comp_bytes,w,h}`가 T1 정의와 T2 사용에서 일치. `compress.step_down_resize`/`encode_to_bytes` 기존 시그니처 사용. 기존 `to_data_uri`/`variants`/`decode_to_file` 불변.
