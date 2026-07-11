# 이미지 다이어트 (Image Diet)

화질은 그대로, 용량만 가볍게. **서버 업로드가 전혀 없는** 100% 브라우저 이미지 압축 도구입니다.
Adobe InDesign의 이미지 다운샘플링 방식에서 영감을 받았습니다 — 300KB 이미지를 60KB로 줄이고,
HTML에 그대로 붙여넣을 수 있는 Base64 문자열까지 뽑아줍니다.

## 기능

- **화질 유지 다운사이징** — 반복 절반 축소(step-down resampling)로 계단 현상 없이 깨끗하게 리사이즈
- **목표 용량 모드** — "60KB로 맞춰줘"라고 하면 품질을 이진 탐색으로 자동 조정 (부족하면 해상도까지 자동 축소)
- **품질 우선 모드** — 품질 슬라이더(40~95%)로 직접 조절
- **형식 변환** — 자동(WebP 우선) / WebP / JPEG / PNG, 투명 배경은 채움색 지정 가능
- **Base64 · HTML 출력** — 결과물을 Data URI, `<img>` 태그, CSS `background-image` 문자열로 복사 → HTML 파일에 그대로 임베드해 오프라인 사용
- **Base64 디코더** — 문자열을 다시 이미지 파일로 복원 (형식 자동 감지)
- **일괄 처리 + ZIP 저장** — 여러 장을 한 번에, 의존성 없는 자체 ZIP 생성기 내장
- **개인정보 보호** — 재인코딩 과정에서 EXIF(GPS 위치 등) 메타데이터 자동 제거, 네트워크 전송 0회
- **PWA + 오프라인** — 한 번 열면 인터넷 없이도 동작, 홈 화면에 설치 가능
- 드래그&드롭, 클립보드 붙여넣기(Ctrl+V), 다크 모드, 원본 비교(썸네일 꾹 누르기)

## GitHub Pages로 배포하기

빌드 과정이 없으므로 이 폴더를 그대로 올리면 됩니다.

### 방법 A — 웹 UI

1. GitHub에서 새 저장소를 만듭니다 (예: `image-diet`).
2. 이 폴더의 파일을 업로드하고 커밋합니다.
3. 저장소 **Settings → Pages** 에서 Source를 `Deploy from a branch`, Branch를 `main` / `(root)`로 지정합니다.
4. 몇 분 뒤 `https://<아이디>.github.io/image-diet/` 에서 열립니다.

### 방법 B — 명령줄 (gh CLI)

```bash
git init -b main
git add .
git commit -m "image diet"
gh repo create image-diet --public --source=. --push
gh api -X POST "repos/{owner}/image-diet/pages" -f "source[branch]=main" -f "source[path]=/"
```

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `index.html` | 앱 전체 (HTML + CSS + JS 올인원, 외부 의존성 0) |
| `sw.js` | 오프라인 캐시용 서비스 워커 |
| `manifest.json` / `icon.svg` | PWA 설치 정보 |

> `index.html` **한 파일만 따로 저장해도** 어떤 브라우저에서든 오프라인으로 동작합니다.

## 기술 노트

- 리사이즈: 2배 이하가 될 때까지 절반씩 줄인 뒤 마지막에 목표 크기로 그리는 step-down 방식 (`imageSmoothingQuality: high`)
- 목표 용량: 품질 0.30~0.95 구간 이진 탐색 6회 + 미달 시 해상도 0.78배씩 축소 재시도
- WebP 인코딩을 지원하지 않는 브라우저(Safari 등)에서는 JPEG/PNG로 자동 대체
- ZIP은 무압축(STORE) 방식 자체 구현 — 이미지가 이미 압축돼 있어 재압축이 무의미하기 때문
