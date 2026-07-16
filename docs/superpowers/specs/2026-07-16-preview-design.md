# 미리보기 (4개 탭) 설계

작성일: 2026-07-16
선행: [데스크톱 툴킷](2026-07-16-desktop-toolkit-design.md) (탭 4개 압축/Base64/SVG/PDF 완료)

## 목적

각 탭에 **미리보기**를 추가한다. SVG·PDF는 출력 파일을 파싱해 렌더링하는 게 아니라,
**이미 가진 원본 데이터에서 직접 래스터화**해 Pillow 이미지를 만들고 `ImageTk`로 표시한다.
그래서 추가 pip 의존성이 없다(Pillow 내장 `ImageTk` 사용).

## 확정된 결정

| 항목 | 결정 |
| --- | --- |
| 범위 | 4개 탭 전부 |
| SVG 갱신 | 슬라이더/프리셋 변경 시 **자동(≈400ms 디바운스)** |
| SVG 표시 | **결과만**(벡터화 결과 래스터) |
| PDF 표시 | **첫 페이지 썸네일 + "1 / N 페이지" 라벨**, 페이지 방식(이미지/A4) 변경 시 갱신 |
| 압축 표시 | **원본 썸네일**(설정 화면) + 압축 후 결과 썸네일 (before→after) |
| Base64 표시 | 인코딩 대상 **원본 썸네일** |
| 표시 방법 | `PIL.ImageTk.PhotoImage` (Pillow 내장, 추가 의존성 아님) |
| 스레드 | 무거운 래스터화는 백그라운드, `PhotoImage` 생성·표시는 메인 스레드 |

## 구조

로직 모듈에 **PIL 이미지를 반환하는** 래스터화 함수를 추가(여전히 tkinter 미의존 → WSL pytest 가능).
`ImageTk` 변환은 UI(뷰/widgets)에서만 한다.

| 파일 | 추가/변경 | 역할 |
| --- | --- | --- |
| `shell/svgtool.py` | `rasterize(img, opts, box=None) -> PIL.Image` | 벡터화 추적 루프를 Pillow `ImageDraw.polygon`으로 색 채워 그림. 베지어는 루프 점으로 근사. `box` 지정 시 그 안에 맞춤. |
| `shell/pdftool.py` | `page_preview(path, fit, box) -> PIL.Image` | 첫 페이지를 나타날 모습대로(이미지 크기 / A4 흰 캔버스) 만들어 `box`에 맞춘 썸네일 |
| `shell/widgets.py` | `make_thumb(pil_img, box) -> PIL.Image`, `Preview(tk.Label)` | 비율 유지 축소 + `ImageTk.PhotoImage` 표시(참조 보관, ImageTk import 가드) |
| `shell/view_svg.py` | 미리보기 패널 + 디바운스 | 슬라이더 변경 → after 디바운스 → bg 스레드 `svgtool.rasterize` → 메인 스레드 표시 |
| `shell/view_pdf.py` | 미리보기 패널 | 첫 페이지 썸네일 + 페이지 수, fit 변경 시 갱신 |
| `shell/view_compress.py` | 미리보기 패널 | 원본 썸네일, 압축 후 결과 썸네일 |
| `shell/view_base64.py` | 미리보기 패널 | 원본 썸네일 |

## 표시 컴포넌트 (widgets)

- `make_thumb(pil_img, box)` — 비율 유지로 `box`(예: (260,200)) 안에 들어가게 축소한 `PIL.Image`. (PIL만, WSL 테스트 가능)
- `class Preview(tk.Label)` — `set(pil_img)`: 내부에서 `ImageTk.PhotoImage` 생성, `self.configure(image=..)`, **참조를 인스턴스에 보관**(GC 방지). `ImageTk` import 실패 시 조용히 텍스트 "(미리보기 불가)"로 대체.
- ImageTk는 Pillow 내장이며 tkinter 컨텍스트(Windows)에서 동작. widgets에서 지연 import.

## 각 탭 동작

### SVG (view_svg)
- 파라미터/프리셋 변경 → `after(400ms)` 디바운스(직전 예약 `after_cancel`).
- 발화 시 백그라운드 스레드에서 `svgtool.rasterize(img, opts, box=(260,220))` → PIL 이미지.
- 메인 스레드(`self.after` + `winfo_exists` 가드)에서 `Preview.set(img)`.
- 첫 진입 시 1회 자동 렌더. [SVG 변환]은 파일 저장(기존 그대로).
- 큰 이미지는 미리보기 해상도(box)로 작아 빠름. 저장용 `vectorize`와 별개.

### PDF (view_pdf)
- 첫 페이지 `pdftool.page_preview(files[0], fit, box=(220,300))` 표시 + "1 / N 페이지".
- fit 세그먼트(이미지/A4) 변경 시 갱신. (동기 렌더 — 썸네일 1장이라 가벼움)

### 압축 (view_compress)
- 설정 화면: 첫 이미지 원본 썸네일.
- 압축 완료 후: 첫 파일 결과 썸네일(before→after 나란히 또는 교체). box=(180,150).

### Base64 (view_base64)
- 인코딩 섹션에 원본(첫 이미지) 썸네일.

## 스레드·안전

- 무거운 래스터화(SVG)는 백그라운드 스레드가 **PIL 이미지만** 반환. `ImageTk.PhotoImage`는 반드시 **메인 스레드**에서 생성(Tk 객체 규칙).
- 디바운스: `self._pending = self.after(400, run)`; 변경마다 `after_cancel(self._pending)`.
- 파괴된 뷰 가드: 기존 `_post`/`winfo_exists` 패턴 재사용.
- `PhotoImage` 참조를 `Preview`가 보관(사라지면 빈 화면).

## 테스트

- `svgtool.rasterize`: 결과가 `PIL.Image`, 크기가 box 이내, 모드 RGB/RGBA. 작은 합성 이미지로 결정성.
- `pdftool.page_preview`: `PIL.Image`, A4 모드는 595:842 비율의 축소본(box 이내), 이미지 모드는 원본 비율.
- `widgets.make_thumb`: 비율 유지 축소(box 초과 안 함). (PIL만 — WSL)
- 뷰 미리보기·디바운스: Windows 위젯 스모크(패널 생성, set 호출, 디바운스 예약/취소 무크래시).

## 정직한 한계

- SVG 미리보기는 **저장 SVG의 정확한 렌더가 아니라** 같은 추적 데이터의 Pillow 래스터 근사(베지어를 폴리라인으로). 시각적으로 충분하나 픽셀 동일하지는 않음.
- 순수 Python 래스터화라 아주 큰 이미지·고색상에서 미리보기가 수백 ms 걸릴 수 있음(box로 작게 유지해 완화, 백그라운드 스레드라 창은 안 멈춤).
- 창이 미리보기(≈220–260px)만큼 커짐.

## 범위 밖 (YAGNI)

- 원본↔결과 비교 슬라이더/드래그(결과만 표시로 결정).
- PDF 전 페이지 넘겨보기(첫 페이지만).
- 실제 SVG/PDF 파일 렌더러 도입(의존성 추가 회피).
