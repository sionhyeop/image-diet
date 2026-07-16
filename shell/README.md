# 이미지 다이어트 — 탐색기 우클릭 압축 (Windows)

웹앱을 열지 않고, 탐색기에서 이미지를 **우클릭**해 바로 압축합니다.

## 요구 사항
- Windows 10/11
- Python 3.x + Pillow (`pip install pillow`)

## 설치
1. `install.bat` 실행 (관리자 권한 불필요).
2. 이미지 파일을 우클릭 → **"이미지 다이어트로 압축"** (Windows 11은 "더 많은 옵션 표시" 안에 아이콘과 함께 표시).

## 사용
- 작은 창에서 **목표 용량(KB)** 과 **출력 형식**(자동/WebP/JPEG/PNG)을 고르고 [압축].
- 결과는 원본과 **같은 폴더**에 `photo1.webp`처럼 숫자만 붙여 저장됩니다. 원본은 그대로.
- 여러 장을 선택해 우클릭하면 같은 설정으로 일괄 처리됩니다.

## 제거
- `uninstall.bat` 실행 (또는 `uninstall.reg` 더블클릭).

## 구성
| 파일 | 역할 |
| --- | --- |
| `compress.py` | 압축 엔진 (Pillow) |
| `compress_gui.pyw` | Tkinter 작은 창 |
| `assets/imagediet.ico`, `logo32.png` | 메뉴 아이콘·창 로고 |
| `install.bat` | 우클릭 메뉴 등록 |
| `uninstall.bat` / `uninstall.reg` | 우클릭 메뉴 제거 |
| `test_compress.py` | 엔진 단위 테스트 |
