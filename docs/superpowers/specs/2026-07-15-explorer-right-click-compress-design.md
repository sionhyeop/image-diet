# 탐색기 우클릭 이미지 압축 (Image Diet Shell)

작성일: 2026-07-15

## 목적

기존 웹앱 **이미지 다이어트**(서버 없는 브라우저 이미지 압축 도구)의 핵심 기능을,
Windows 파일 탐색기에서 **이미지를 우클릭 한 번**으로 쓸 수 있게 만든다.
"브라우저 열기 → 드래그 → 옵션 → 다운로드" 흐름을,
"우클릭 → 작은 창에서 목표 용량·형식 고르기 → 옆에 저장" 흐름으로 단축한다.

## 확정된 결정 사항

| 항목 | 결정 |
| --- | --- |
| 동작 방식 | 작은 선택창을 띄워 옵션 고르고 처리 (완전 무음 아님) |
| 압축 엔진 | Python + Pillow로 재구현 (웹앱 알고리즘 포팅) |
| 설치 | Windows에 Python 설치 전제 |
| 창 UI | Tkinter (Python 내장) |
| 우클릭 등록 | `.reg` 파일 (`HKEY_CURRENT_USER`만 사용) |
| 저장 위치 | 원본과 **같은 폴더** |
| 파일명 | 접미사 없이 **뒤에 숫자만** — `photo.jpg` → `photo1.webp`, 충돌 시 `photo2.webp` … |
| 일괄 처리 | 여러 파일 선택 후 우클릭 → 같은 설정으로 전부 처리 (지원) |
| 창 옵션 | **목표 용량(KB)** + **출력 형식**(자동/WebP/JPEG/PNG) 2개만 |
| 원본 | 절대 건드리지 않음 (덮어쓰기 없음) |

## 전체 구조 · 동작 흐름

```
탐색기에서 이미지 1장 이상 선택
  └─ 우클릭 → "이미지 다이어트로 압축"
       └─ compress_gui.pyw 실행 (선택 파일 경로들이 argv로 전달)
            ├─ 작은 Tkinter 창: [목표 용량 KB] [출력 형식 ▾] [압축]
            ├─ 압축 실행 (compress.py → Pillow) — 파일마다 진행 표시
            └─ photo.jpg → photo1.webp 로 같은 폴더에 저장, 완료 표시
```

## 컴포넌트 (파일 구성)

기존 저장소 안 `shell/` 폴더에 둔다. 웹앱(`index.html`)과 한 저장소에 공존.

| 파일 | 역할 | 의존성 |
| --- | --- | --- |
| `shell/compress.py` | 압축 엔진(라이브러리, UI 없음). 순수 함수 중심, 단독 테스트 가능 | Pillow |
| `shell/compress_gui.pyw` | Tkinter 작은 창. `sys.argv`로 파일 경로 받아 옵션 입력 후 `compress.py` 호출. `.pyw`라 콘솔 창 안 뜸 | tkinter(내장), compress.py |
| `shell/install.reg` | 우클릭 메뉴 등록 | — |
| `shell/uninstall.reg` | 우클릭 메뉴 해제 | — |
| `shell/install.bat` | Python 경로 자동 탐지 + `.reg` 적용을 한 번에 (사용자가 경로 직접 입력 안 하게) | — |
| `shell/test_compress.py` | `compress.py` 단위 테스트 | pytest, Pillow |

### compress.py 인터페이스 (설계 의도)

```python
def compress_image(
    src_path: str,
    target_kb: int | None,      # 목표 용량 (None이면 형식 기본 품질)
    out_format: str,            # "auto" | "webp" | "jpeg" | "png"
) -> str:                       # 저장된 새 파일 경로 반환
    ...
```

- **알고리즘 (웹앱 포팅)**:
  - step-down 리사이즈: 목표의 2배 이하가 될 때까지 절반씩 축소 후 마지막에 목표 크기로 그림 (품질 유지). 단, 이 기능에서는 해상도 축소는 목표 용량을 못 맞출 때만 발동.
  - 목표 용량 모드: 품질 이진 탐색(대략 0.30~0.95, 약 6회)으로 목표 KB 이하에 맞춤. 그래도 미달이면 해상도를 0.78배씩 줄여 재시도.
  - "자동" 형식 = WebP 우선 (웹앱과 동일). 투명 PNG는 WebP로 투명 유지.
  - 출력 파일명: 원본과 같은 폴더, `stem` + 숫자 + 새 확장자. `photo1.webp`부터 시작, 존재하면 숫자 증가.

## 작은 창 (UI)

```
┌─ 이미지 다이어트 ───────────────┐
│  파일 3개 선택됨                 │
│                                 │
│  목표 용량   [ 200 ] KB          │
│  출력 형식   [ 자동(WebP) ▾ ]    │
│                                 │
│         [ 압축 ]   [ 취소 ]      │
│  ─────────────────────────────  │
│  photo1.jpg  →  48KB  ✓          │
│  photo2.png  →  처리 중…         │
└─────────────────────────────────┘
```

- 옵션 2개만: **목표 용량(KB)**, **출력 형식**(자동/WebP/JPEG/PNG).
- 마지막 사용 설정을 `%APPDATA%\image-diet-shell\settings.json`에 저장 → 다음엔 [압축]만 누르면 됨.
- 다중 선택 시 전부 같은 설정으로 일괄 처리, 각 파일 결과를 리스트로 표시.
- 실패한 파일은 건너뛰고 ✗ 표시 — 하나 실패해도 나머지 계속.

## 저장 · 형식 규칙

- 원본과 같은 폴더에 새 파일. 원본 절대 미변경.
- 파일명: 접미사 없이 숫자만. `photo.jpg` → `photo1.webp`, 충돌 시 `photo2.webp`, `photo3.webp` …
- "자동" = WebP 우선, 투명 유지.

## 우클릭 등록 (레지스트리)

- `HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\<.ext>\shell\...` 에 등록.
- 대상 확장자: `.jpg .jpeg .png .webp .bmp`.
- 다중 선택 지원을 위해 각 파일마다 실행 대신 한 번에 넘기는 방식 검토 (기본 `%1`은 파일마다 인스턴스가 뜨므로, 필요 시 shell verb에 `MultiSelectModel`을 지정해 한 창에서 처리).
- `HKEY_CURRENT_USER`만 사용 → 관리자 권한 불필요, 시스템 전역 영향 없음.
- `install.bat`이 Python 실행 파일(`pythonw.exe`) 경로를 자동 탐지해 `.reg` 템플릿에 채워 적용.

## 테스트 · 안전장치

- `test_compress.py`: 작은 샘플 이미지로 (1) 목표 용량 이하로 나오는지, (2) 형식별 인코딩(webp/jpeg/png), (3) 파일명 충돌 시 숫자 증가, (4) 원본 미변경을 검증.
- `.reg`는 되돌릴 수 있게 `uninstall.reg` 동봉.
- 원본 덮어쓰기 없음 → 데이터 손실 위험 없음.

## 범위 밖 (YAGNI)

- 배경 제거, SVG 변환, 메타데이터 편집, Base64 출력 등 웹앱의 고급 기능은 이 우클릭 도구에 넣지 않는다 (웹앱에서 계속 제공).
- 품질 슬라이더·최대 해상도 제한 옵션은 창에 넣지 않는다 (최소 UI).
- 완전 무음(창 없는) 모드는 이번 범위 밖.
