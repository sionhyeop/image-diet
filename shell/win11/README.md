# 이미지 다이어트 — Win11 첫 화면 우클릭 메뉴

우클릭 **첫 화면**("더 많은 옵션 표시" 없이)에 아이콘과 함께 "이미지 다이어트로 압축"을 띄웁니다.
셸 확장 DLL은 선택 파일을 기존 Python 압축 창으로 넘기기만 합니다.

## 요구 사항
- Windows 10 2004+ / 11
- Python 3.x + Pillow (`pip install pillow`)
- (빌드 시) Visual Studio 2022+ C++ 워크로드, Windows SDK

## 빌드 → 설치
```powershell
# 1) 자산 생성 (최초 1회)
python make_assets.py
# 2) DLL·패키지 빌드 + 자체서명
powershell -ExecutionPolicy Bypass -File build.ps1
# 3) 설치 (관리자 PowerShell)
powershell -ExecutionPolicy Bypass -File install.ps1
```

## 삭제
```powershell
# 관리자 PowerShell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

## 무충돌 재설치
`install.ps1`은 실행 시 먼저 이전 흔적(패키지·인증서·설정·legacy 항목)을 모두 지운 뒤 새로 설치합니다.
따라서 **몇 번을 반복 설치/삭제해도** 메뉴·인증서·등록이 중복되지 않습니다.

## 문제 해결
- 메뉴가 안 보이면: `install.ps1` 재실행 후 Explorer가 재시작됐는지 확인, 또는 로그아웃/로그인.
- "올바르게 설치되지 않았습니다" 대화상자: `HKCU\Software\ImageDiet` 값이 비었을 때 → `install.ps1` 재실행.
- 폴더를 옮겼다면: 옮긴 위치에서 `install.ps1` 재실행(경로 자동 갱신).

## 간단 버전(무관리자)
첫 화면 대신 "더 많은 옵션 표시" 안이면 충분하다면, 상위 폴더의 `../install.bat`(레지스트리 방식, 관리자 불필요)을 쓰세요.
