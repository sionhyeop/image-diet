#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# 0) 초기화: 이전 흔적 싹 제거 (반복 설치해도 무충돌)
& "$here\_cleanup.ps1"

# 1) 실행 경로 확정
$pyw = $null
foreach ($c in @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\pythonw.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe")) {
    if (Test-Path $c) { $pyw = $c; break }
}
if (-not $pyw) {
    $pyw = (& py -3 -c "import os,sys;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2>$null)
}
if (-not $pyw -or -not (Test-Path $pyw)) { throw "pythonw.exe 를 찾을 수 없습니다. Python 설치 후 다시 실행하세요." }

$gui  = (Resolve-Path "$here\..\compress_gui.pyw").Path
$icon = (Resolve-Path "$here\assets\imagediet.ico").Path

# 2) DLL이 읽을 런타임 설정 기록
New-Item -Path 'HKCU:\Software\ImageDiet' -Force | Out-Null
Set-ItemProperty 'HKCU:\Software\ImageDiet' -Name 'Pythonw'   -Value $pyw
Set-ItemProperty 'HKCU:\Software\ImageDiet' -Name 'GuiScript' -Value $gui
Set-ItemProperty 'HKCU:\Software\ImageDiet' -Name 'IconPath'  -Value $icon

# 3) 자체서명 인증서 신뢰 등록
$cer = Join-Path $here 'out\ImageDiet.cer'
if (-not (Test-Path $cer)) { throw "out\ImageDiet.cer 없음. 먼저 build.ps1 실행." }
Import-Certificate -FilePath $cer -CertStoreLocation 'Cert:\LocalMachine\Root'         | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople' | Out-Null

# 3.5) 개발자 모드(사이드로드) 활성화 — runFullTrust 자체서명 패키지 등록에 필요.
#      인증서가 신뢰돼 있어도, 비스토어 전체신뢰 패키지는 이 스위치가 있어야 배포됨.
$unlock = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'
New-Item -Path $unlock -Force | Out-Null
Set-ItemProperty -Path $unlock -Name 'AllowAllTrustedApps'              -Value 1 -Type DWord
Set-ItemProperty -Path $unlock -Name 'AllowDevelopmentWithoutDevLicense' -Value 1 -Type DWord

# 4) 패키지 등록
$msix = Join-Path $here 'out\ImageDietShell.msix'
if (-not (Test-Path $msix)) { throw "out\ImageDietShell.msix 없음. 먼저 build.ps1 실행." }
Add-AppxPackage -Path $msix

# 5) Explorer 재시작으로 메뉴 캐시 갱신
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer
Write-Host "설치 완료. 이미지 우클릭 첫 화면에 '이미지 다이어트로 압축' 이 나타납니다."
