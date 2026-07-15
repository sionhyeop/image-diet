# Win11 네이티브 우클릭 메뉴 + 아이콘 + 창 다듬기 설계

작성일: 2026-07-15
선행: [탐색기 우클릭 이미지 압축](2026-07-15-explorer-right-click-compress-design.md) (엔진·GUI·legacy .reg 방식은 이미 구현 완료)

## 목적

기존 legacy 방식(우클릭 → "더 많은 옵션 표시" 안에 표시)을 넘어,
**Windows 11 우클릭 첫 화면**에 "이미지 다이어트로 압축"을 아이콘과 함께 띄운다.
동시에 압축 창을 **크롬 익스텐션 팝업 같은 깔끔한 UI**로 다듬는다.
압축 엔진·GUI 로직은 그대로 재사용하고, 새로 만드는 셸 확장 DLL은 "선택 파일을 pythonw로 넘기는" 얇은 껍데기만 담당한다.

## 최우선 원칙: 무충돌 재설치 (사용자 최중요 요구)

설치·삭제를 **몇 번을 반복해도** 중복 메뉴·중복 인증서·잔여 등록이 남지 않아야 한다. 이를 위해:

1. **모든 식별자를 고정 상수로 못 박는다** — 재빌드해도 변하지 않음:
   - 패키지 Name: `ImageDiet.ShellExtension`
   - Publisher: `CN=ImageDiet Dev` (인증서 Subject와 정확히 일치해야 함)
   - COM CLSID: 고정 GUID 1개 (매니페스트·DLL·레지스트리에서 동일 값 재사용)
   - 인증서 Subject: `CN=ImageDiet Dev` (설치 스크립트가 이 Subject로 찾고 지움)
2. **install.ps1은 "초기화 후 설치" 방식** — 먼저 uninstall 로직을 실행해 이전 흔적(패키지·인증서·legacy reg)을 싹 지운 뒤 새로 설치한다. 그래서 처음 설치든 재설치든 항상 같은 깨끗한 결과.
3. **패키지 Name이 고정**이므로 `Add-AppxPackage` 재등록은 중복 생성이 아니라 **교체**가 된다.
4. **legacy .reg 항목 제거**를 install.ps1이 항상 수행 → "더 많은 옵션" 안 중복 노출 방지.
5. 설치·삭제 후 **Explorer 재시작**으로 메뉴 캐시를 강제 갱신.

## 구조

```
[셸 확장 DLL (C++/WRL)]  ── 얇은 껍데기 (≈150줄 보일러플레이트)
   IExplorerCommand 구현: 제목·아이콘·활성조건·Invoke
   Invoke: 선택된 IShellItemArray → 경로 추출 → pythonw.exe compress_gui.pyw <files> 실행
        │
        ▼
[Python GUI (기존, UI만 다듬음)]  ── compress_gui.pyw + compress.py 재사용
   크롬 팝업풍 창에서 목표 용량·형식 고르고 압축
```

압축 엔진·GUI **기능은 안 바뀐다**. DLL은 오직 연결만 담당. 다중 선택도 DLL이 한 번에 넘겨 **한 창**에서 처리(legacy .bat 방식의 다중선택 숙제가 여기선 깔끔히 해결).

## 컴포넌트 (파일 구성) — `shell/win11/` 새 폴더

| 파일 | 역할 |
| --- | --- |
| `src/ImageDietCommand.h/.cpp` | `IExplorerCommand` 구현 (GetTitle/GetIcon/GetState/Invoke) |
| `src/dllmain.cpp` | COM 서버 진입점 (DllGetClassObject, DllCanUnloadNow) |
| `src/ImageDietShell.def` | export 정의 |
| `src/pch.h` | WRL/shell 헤더 프리컴파일 |
| `ImageDietShell.vcxproj` | Visual Studio C++ DLL 프로젝트 (MSBuild) |
| `package/AppxManifest.xml` | 스파스 MSIX 매니페스트 — COM 서버 + `windows.fileExplorerContextMenus` 확장, 고정 Name/Publisher/CLSID |
| `assets/imagediet.ico` | 저장소 로고(`icon-512.png`)에서 생성한 메뉴/창 아이콘 |
| `assets/*.png` | 패키지 필수 로고(Square44/150 등, icon PNG에서 리사이즈) |
| `build.ps1` | MSBuild 빌드 → `makeappx pack` → `signtool sign` |
| `install.ps1` | (관리자) 초기화 후 설치: 인증서 신뢰 등록 + 패키지 등록 + legacy reg 제거 + Explorer 재시작 |
| `uninstall.ps1` | (관리자) 패키지 제거 + 인증서 제거 + Explorer 재시작 |
| `README.md` | 빌드·설치·삭제·문제해결 안내 |

기존 `shell/install.bat`·`shell/uninstall.reg`(legacy 방식)는 **삭제하지 않고 유지**한다. "간단·무관리자 = .bat / 첫 화면 = win11/install.ps1" 두 갈래를 문서로 안내. 단, win11/install.ps1은 실행 시 legacy reg 항목을 지워 중복을 막는다.

## 동작 세부

- **선택 파일 전달**: `IExplorerCommand::Invoke(IShellItemArray* psiItemArray, ...)`에서 각 항목의 `SIGDN_FILESYSPATH` 경로를 뽑아, `pythonw.exe "<...>\compress_gui.pyw" "f1" "f2" ...` 커맨드라인으로 `CreateProcess`/`ShellExecuteEx` 실행.
- **pythonw 경로 탐지**: DLL이 (1) `py -3`로 경로 질의 → (2) `HKCU/HKLM` Python 레지스트리 → (3) 실패 시 오류 MessageBox. (Python 경로는 DLL 로드 시점이 아니라 Invoke 시점에 1회 탐지)
- **활성 조건(GetState)**: 선택 항목이 이미지 확장자(.jpg/.jpeg/.png/.webp/.bmp)일 때만 `ECS_ENABLED`, 아니면 `ECS_HIDDEN`. 매니페스트에서도 해당 확장자에만 연결.
- **제목/아이콘**: GetTitle → "이미지 다이어트로 압축", GetIcon → `imagediet.ico` 경로.

## 창 다듬기 (Tkinter) — 크롬 익스텐션 팝업 톤

- **컴팩트 팝업**(≈360px 폭), 흰 카드 배경, 넉넉한 여백(패딩 16~20)
- 상단 **로고 + 제목 헤더** 한 줄
- **강조색 [압축] 버튼**(파란 계열), 보조 [취소]는 연한 테두리 버튼
- 입력: "목표 용량 [ 200 ] KB" · "형식 [ 자동 ▾ ]" 정렬된 2행
- 결과는 **진행바 + 파일별 ✓/✗ 행** (텍스트 나열 대신)
- **다크모드 자동 대응**(Windows 앱 테마 레지스트리 `AppsUseLightTheme` 감지 → 색 스와프)
- 기능·옵션은 그대로(목표 용량 + 형식). 겉모습만 개선. `compress.py` 미변경.

> Tkinter는 창 모서리 라운딩·그림자는 어렵다. "둥근 창" 대신 **플랫하고 정돈된 카드 + 명확한 강조 버튼 + 좋은 여백/타이포**로 크롬 팝업의 *느낌*을 낸다. (네이티브 라운드 코너까지 원하면 향후 WinUI 재작성이 필요 — 이번 범위 밖)

## 빌드·검증 전략

- **C++ 빌드**: WSL에서 `cmd.exe /c` 경유로 `MSBuild ImageDietShell.vcxproj` 컴파일 성공 확인.
- **패키징·서명**: `makeappx pack` + `signtool sign` 산출물(.msix) 생성 확인, `signtool verify`로 서명 확인.
- **매니페스트 정합성**: Publisher == 인증서 Subject == 고정 상수인지 교차 확인 (불일치 시 등록 실패).
- **실제 메뉴 노출·클릭·다중선택·아이콘**: Windows에서 **수동** 확인 (관리자 install.ps1 실행 → Explorer 재시작 → 우클릭 첫 화면 확인).
- **무충돌 재설치 검증**(수동, 최중요): install → uninstall → install → install 반복 후 (a) 메뉴 항목이 1개만, (b) 인증서 저장소에 `CN=ImageDiet Dev` 1개만, (c) `Get-AppxPackage ImageDiet.ShellExtension` 1개만 남는지 확인.
- **창 다듬기**: `py_compile` + Windows 수동 시각 확인.

## 범위 밖 (YAGNI)

- WinUI/네이티브 라운드 코너 창 재작성 (Tkinter 유지)
- Microsoft Store 배포 (자체 서명 사이드로드만)
- 압축 엔진·옵션 변경 (기존 그대로)
- legacy .bat 방식 삭제 (병행 유지)

## 리스크 (정직하게)

- 스파스 MSIX + COM 셸 확장 + 자체 서명 인증서는 **실패 지점이 많다**(매니페스트 정합성, 인증서 신뢰, Explorer 캐시, 사이드로드 정책). 첫 등록이 한 번에 안 될 수 있고 Windows에서 반복 시도·재시작이 필요할 수 있다.
- 관리자 권한·인증서 신뢰 저장소 조작이 필요 → 개인 PC 한정 도구로 적합, 배포용은 아님.
