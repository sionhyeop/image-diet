# 이미지 다이어트 데스크톱 툴킷 (탭 4개) 설계

작성일: 2026-07-16
선행: [탐색기 우클릭 이미지 압축](2026-07-15-explorer-right-click-compress-design.md) (압축 엔진·legacy 우클릭·크롬 팝업 UI 완료)

## 목적

지금까지의 단일 기능("우클릭 → 압축")을, 웹앱과 같은 **다기능 이미지 툴킷**으로 확장한다.
한 우클릭 항목으로 열리는 **탭 창**(압축 / Base64 / SVG / PDF) 안에서 4가지 도구를 쓴다.
복수 선택 시 **한 창에서** 같은 설정으로 일괄 처리되게 하고, 압축은 파일별·전체 절감량을 보여준다.

## 확정된 결정

| 항목 | 결정 |
| --- | --- |
| 배치 | **한 창 + 상단 탭**(압축/Base64/SVG/PDF), 우클릭 항목은 1개 |
| SVG | **웹앱 알고리즘 충실 포팅** (index.html 2949–3520행) |
| 진행 | 한 번에 전부(단일 스펙·계획, 태스크로 분할 실행) |
| 복수 선택 | **단일 인스턴스 취합**으로 한 창 처리 |
| 절감 표시 | 파일별 `원본→결과` + 전체 요약 |
| PDF | 선택 이미지들을 **한 PDF로 합치기** 기본(페이지=이미지 크기, A4맞춤 옵션) |
| SVG 미리보기 | **없음**(Tkinter 한계) — 변환·저장 후 "결과 열기"로 대체 |
| 진입점 | 파일명 `compress_gui.pyw` 유지 → **재설치 불필요** |
| 의존성 | Python + Pillow만(무추가 의존) |

## 구조 (모듈 분리)

로직과 UI를 분리한다. **로직 모듈은 tkinter를 import하지 않아** WSL에서 pytest로 검증 가능하다. UI(뷰/창)는 Windows에서 위젯 트리 스모크 + 수동 확인한다.

| 파일 | 역할 | 의존 | 테스트 |
| --- | --- | --- | --- |
| `shell/compress.py` | 압축 엔진 (기존, 불변) | Pillow | WSL pytest |
| `shell/b64tool.py` | Base64 인코딩/디코딩 | 표준 라이브러리 | WSL pytest |
| `shell/svgtool.py` | 이미지→SVG 벡터화 | Pillow | WSL pytest |
| `shell/pdftool.py` | 이미지→PDF | Pillow | WSL pytest |
| `shell/singleinstance.py` | 복수선택 소켓 취합 | 표준 라이브러리 | WSL pytest |
| `shell/widgets.py` | 공용 UI(round_rect·RoundButton·Segmented·Bar·chip·palette·_human·_elide) | tkinter | Win 스모크 |
| `shell/view_compress.py` | 압축 탭 | widgets, compress | Win 스모크 |
| `shell/view_base64.py` | Base64 탭 | widgets, b64tool | Win 스모크 |
| `shell/view_svg.py` | SVG 탭 | widgets, svgtool | Win 스모크 |
| `shell/view_pdf.py` | PDF 탭 | widgets, pdftool | Win 스모크 |
| `shell/compress_gui.pyw` | 탭 창(진입점): 취합→창→탭 호스팅 | 위 전부 | Win 스모크 |

기존 `compress_gui.pyw`(현재 단일 압축 창)의 UI 로직은 `widgets.py`(공용) + `view_compress.py`(압축 탭)로 옮긴다. 진입점 파일명은 유지한다.

## 복수 선택 → 한 창 (singleinstance.py)

Windows legacy 우클릭 verb는 선택 파일마다 프로세스를 띄운다. 이를 앱 쪽에서 취합한다:

- `coalesce(argv_files, port=51737, window=0.8) -> list[str] | None`
  - `127.0.0.1:<port>` 바인드 시도.
    - **성공(서버)**: 수신 스레드 시작. 자기 argv 파일 + 형제 인스턴스가 보낸 경로를 `window`초 동안 모은 뒤 리스너를 닫고 **합친 리스트 반환**.
    - **실패**: `connect` 시도 → 핸드셰이크 매직 확인 후 자기 파일 경로 전송 → **`None` 반환(형제, 창 없이 종료)**. connect가 우리 서버가 아니거나 실패하면 폴백으로 argv_files 반환(단일 창).
  - 루프백만 사용 → 방화벽·관리자 불필요.
- 진입점: `files = coalesce(argv); if files is None: return`. 서버 인스턴스만 창을 연다.
- 핸드셰이크: 연결 후 매직 문자열 교환으로 우리 서버인지 확인(포트 충돌 오검출 방지).

## 탭 창 (compress_gui.pyw + widgets)

- 헤더: 로고 + "이미지 다이어트".
- **탭 바**: 세그먼트 스타일(압축 / Base64 / SVG / PDF). 탭 전환 시 아래 뷰 교체.
- 활성 탭 뷰가 콘텐츠 영역을 채움. 틸 팔레트·다크모드 자동·화면 중앙 배치는 기존 유지.
- 창은 리사이즈 불가. 탭마다 창 크기가 달라질 수 있어 탭 전환 후 재-center.

## 각 탭

### 압축 (view_compress)
- 기존 UI(목표 용량 + 형식 세그먼트) + [압축].
- **파일별 결과 행**: `원본이름 · 원본크기 → 결과크기` + 성공/실패 칩.
- **전체 요약**: `총 원본 → 총 결과 · N% 가벼워짐`.
- 취합된 다중 파일을 같은 설정으로 일괄 처리.

### Base64 (view_base64 + b64tool)
- **인코딩**: 취합된(첫) 이미지를 Data URI로. 복사 버튼 3종 — Data URI / `<img>` 태그 / CSS `background-image`. 클립보드는 Tk `clipboard_append`.
- **디코딩**: 텍스트 입력(Data URI 또는 순수 Base64) → [이미지로 저장] → 형식 자동 감지 → `filedialog`로 저장.
- b64tool 인터페이스:
  - `to_data_uri(path) -> str`
  - `variants(path) -> {"datauri": str, "imgtag": str, "css": str}`
  - `decode_to_file(text, out_path) -> str` (data URI 헤더 또는 매직바이트로 확장자 결정)

### SVG (view_svg + svgtool)
- 파라미터(웹앱과 동일): 색상 수(2–16), 추적 정밀도(1–5), 외곽선 단순화(0–4), 잡티 제거(0–4), 빈틈 메우기(0–4). 프리셋: 로고/일러스트/사진(웹앱 값 그대로).
- [변환] → `svgtool.vectorize(pil_image, opts) -> svg_str` → 원본 옆 `name1.svg` 저장 → [결과 열기] 버튼(`os.startfile`).
- **미리보기 없음**(Tkinter 한계). 저장 후 열기로 확인.
- 큰 이미지는 벡터화 전 축소(웹앱과 동일 전처리).
- svgtool는 index.html 2949–3520행(quantizePalette, traceLoops, vectorizeToSvg, buildSvgFromEntries, douglasPeucker/bezier 헬퍼)을 **충실 포팅**. Pillow 픽셀 접근 + 순수 Python.
- 인터페이스: `vectorize(img, opts: dict) -> str`, `PRESETS: dict`, `default_opts() -> dict`.

### PDF (view_pdf + pdftool)
- 취합된 이미지들을 **한 PDF로 합치기**(순서=선택순). 파일 목록 표시.
- 옵션: 페이지 = 이미지 크기(기본) / A4 맞춤.
- [PDF 만들기] → `filedialog`로 저장.
- pdftool 인터페이스: `images_to_pdf(paths, out_path, fit="image"|"a4") -> str` (Pillow `save_all`).

## 정직한 한계

- **SVG 실시간 미리보기·비교 슬라이더 없음** — Tkinter가 SVG 렌더를 못 함. 변환·저장 후 외부 열기로 대체.
- **SVG 성능** — 순수 Python이라 큰 이미지는 느릴 수 있어 전처리 축소로 완화.
- **배경 제거·메타데이터 편집** 등 웹앱의 나머지 탭은 이번 범위 밖(요청된 4개만).

## 테스트 전략

- **로직 모듈**(`b64tool`,`svgtool`,`pdftool`,`singleinstance`): tkinter 미의존 → WSL pytest.
  - b64tool: 인코딩 라운드트립(이미지→data URI→디코딩→동일 바이트), 형식 감지.
  - svgtool: 결과가 `<svg`로 시작·`<path` 포함, 색상 수 옵션 반영, 작은 합성 이미지로 결정성.
  - pdftool: 여러 이미지→유효 PDF(%PDF 헤더, 페이지 수), fit 옵션.
  - singleinstance: 로컬 서버+클라이언트 시뮬레이션으로 취합 리스트 검증.
- **뷰/창**: Windows Python으로 위젯 트리 숨김 빌드(라이트+다크) + 수동 확인.
- 기존 `test_compress.py` 회귀 유지.

## 범위 밖 (YAGNI)

- 웹앱의 배경 제거·메타데이터·라이트박스 등 미요청 기능.
- SVG 렌더링 미리보기(렌더러 의존성 추가).
- MSIX/첫화면 메뉴(이미 legacy로 확정).
