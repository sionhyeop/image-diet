# 이미지 다이어트 — 탐색기 우클릭 압축 (Windows)

웹앱을 열지 않고, 탐색기에서 이미지를 **우클릭**해 바로 압축합니다.

## 요구 사항
- Windows 10/11
- Python 3.x + Pillow (`pip install pillow`)

## 설치
1. GitHub에서 저장소를 내려받습니다 — **Code → Download ZIP** 후 압축 해제, 또는 `git clone https://github.com/sionhyeop/image-diet.git`.
2. 이 `shell` 폴더의 `install.bat` 실행 (관리자 권한 불필요).
3. 이미지 파일을 우클릭 → **"이미지 다이어트로 압축"** (Windows 11은 "더 많은 옵션 표시" 안에 아이콘과 함께 표시).

## 사용
- 이미지를 우클릭 → **"이미지 다이어트로 압축"** 선택.
- **4개 탭**(압축/Base64/SVG/PDF) 창이 열립니다:
  - **압축**: 목표 용량(KB)과 출력 형식(자동/WebP/JPEG/PNG)을 고른 후 [압축]. 결과는 같은 폴더에 `photo1.webp`처럼 저장.
  - **Base64**: 이미지를 Data URI 또는 HTML/CSS 코드로 변환해 복사.
  - **SVG**: 선택된 이미지를 벡터 형식으로 변환. 프리셋과 슬라이더로 품질 조정 후 저장.
  - **PDF**: 여러 이미지를 한 PDF 문서로 통합.
- **여러 장을 선택**해 우클릭하면 **한 창**에서 "파일 N개"로 표시되며, 모든 이미지를 한 번에 처리할 수 있습니다.

## 제거
- `uninstall.bat` 실행 (또는 `uninstall.reg` 더블클릭).

## 구성
| 파일 | 역할 |
| --- | --- |
| `compress.py` | 압축 엔진 (Pillow) |
| `b64tool.py` | Base64 변환 엔진 |
| `pdftool.py` | PDF 병합 엔진 |
| `svgtool.py` | SVG 벡터 변환 엔진 |
| `singleinstance.py` | 다중 선택 파일 통합 관리 |
| `widgets.py` | UI 공용 컴포넌트 (버튼, 세그먼트, 아이콘) |
| `compress_gui.pyw` | Tkinter 메인 진입점 (4개 탭 호스팅) |
| `view_compress.py` | 압축 탭 뷰 |
| `view_base64.py` | Base64 탭 뷰 |
| `view_svg.py` | SVG 탭 뷰 |
| `view_pdf.py` | PDF 탭 뷰 |
| `assets/imagediet.ico`, `logo32.png` | 메뉴 아이콘·창 로고 |
| `install.bat` | 우클릭 메뉴 등록 |
| `uninstall.bat` / `uninstall.reg` | 우클릭 메뉴 제거 |
| `test_compress.py` | 압축 엔진 단위 테스트 |
| `test_b64tool.py` | Base64 엔진 단위 테스트 |
| `test_pdftool.py` | PDF 엔진 단위 테스트 |
| `test_svgtool.py` | SVG 엔진 단위 테스트 |
| `test_singleinstance.py` | 파일 통합 단위 테스트 |
