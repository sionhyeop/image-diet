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
- **일괄 처리 + ZIP 저장** — 여러 장을 한 번에, 폴더째 드래그&드롭도 지원, 의존성 없는 자체 ZIP 생성기 내장
- **배경 제거** — 테두리 색 k-means 학습 + 연결영역 플러드필로 자동 제거(모델 다운로드 없이 완전 오프라인), 원본↔결과 비교 바, 브러시(지우기/복원) 부분 편집 + 실행취소, PNG 최대화질·WebP/JPEG 압축 다운로드. **여러 장을 올리면 일괄 배경 제거**(결과 미리보기 + ZIP)
- **요소 추출 (AI 인스턴스 분리)** — 색 기반 추출에 더해, 버튼을 눌러 SlimSAM 모델(약 13MB, 첫 사용 시 외부에서 1회 다운로드 후 오프라인)을 받으면 **클릭 한 점으로 그 물체만 정확히** 떼어냄 — 색이 비슷한 물체도 물체 단위로 분리
- **격자 분할 (n×m)** — 이미지를 가로·세로 조각 수대로 균등 분할. 자를 위치를 원본 위에 가이드라인으로 미리 보여주고, 조각별 개별 저장 또는 ZIP 일괄 저장. 자르면서 형식(WebP/JPEG/PNG)과 품질을 지정해 용량도 함께 줄임
- **이미지 → SVG 벡터 변환** — 색상 양자화(median cut) + 외곽선 추적 + 패스 단순화를 자체 구현. 색상 수·추적 정밀도·외곽선 단순화·잡티 제거를 개별 조절, 프리셋(로고/일러스트/사진) 제공, 원본↔SVG 드래그 비교 슬라이더
- **메타데이터 보기·편집** — JPEG EXIF와 PNG 텍스트 청크를 픽셀 손상 없이 읽고 수정 (설명·작가·저작권·촬영일시·GPS), 전체 제거도 한 번에. 파서/라이터 자체 구현
- **압축 시 메타데이터 선택** — 기본은 EXIF 제거(개인정보 보호), ‘메타데이터 유지하기’를 켜면 원본 EXIF를 압축된 JPEG·PNG에 복사 (방향 태그는 자동 보정)
- **미리보기 라이트박스** — 결과를 클릭 한 번으로 크게 확인
- **개인정보 보호** — 재인코딩 과정에서 EXIF(GPS 위치 등) 메타데이터 자동 제거, 네트워크 전송 0회
- **PWA + 오프라인** — 한 번 열면 인터넷 없이도 동작, 홈 화면에 설치 가능
- **데스크톱 우클릭 압축(Windows)** — 탐색기에서 이미지를 우클릭해 바로 압축(아이콘 포함). 설치·사용법은 [`shell/README.md`](shell/README.md) 참고
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

## 데스크톱(Windows) 설치 — GitHub에서

탐색기 우클릭으로 쓰는 데스크톱 모드는 이 저장소를 내려받아 설치합니다. (Python + Pillow 필요: `pip install pillow`)

1. **저장소 내려받기** — 아래 중 하나:
   - GitHub 페이지에서 **Code → Download ZIP** 후 압축 해제, 또는
   - `git clone https://github.com/sionhyeop/image-diet.git`
2. **설치** — 압축 해제/클론한 폴더의 `shell\install.bat` 더블클릭 (관리자 권한 불필요).
3. 이미지 파일을 우클릭 → **"이미지 다이어트로 압축"** → 압축/Base64/SVG/PDF 탭 창이 열립니다.

> `shell` 폴더는 통째로 한 자리에 두세요. 옮겼다면 옮긴 위치에서 `install.bat`을 다시 실행하면 경로가 갱신됩니다. 제거는 `shell\uninstall.bat`. 자세한 내용은 [`shell/README.md`](shell/README.md).

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
- SVG 변환: median-cut 색상 양자화 → 색별 마스크 경계 에지 추적(Eulerian 루프 분해, fill-rule:evenodd) → Douglas-Peucker 단순화 → 이차 베지어 스무딩
- WebP 인코딩을 지원하지 않는 브라우저(Safari 등)에서는 JPEG/PNG로 자동 대체
- ZIP은 무압축(STORE) 방식 자체 구현 — 이미지가 이미 압축돼 있어 재압축이 무의미하기 때문
