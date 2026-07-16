# 빌드: MSBuild(DLL+스텁) -> 레이아웃 구성 -> makeappx pack -> 자체서명 -> signtool sign
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit  = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64'
$msb  = 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe'
$subject = 'CN=ImageDiet Dev'

# 1) 빌드
& $msb "$here\ImageDietShell.vcxproj"    /p:Configuration=Release /p:Platform=x64 /v:m
& $msb "$here\ImageDietLauncher.vcxproj"  /p:Configuration=Release /p:Platform=x64 /v:m

# 2) 패키지 레이아웃 구성
$layout = Join-Path $here 'layout'
if (Test-Path $layout) { Remove-Item $layout -Recurse -Force }
New-Item -ItemType Directory -Path $layout, "$layout\assets" | Out-Null
Copy-Item "$here\package\AppxManifest.xml" $layout
Copy-Item "$here\bin\ImageDietShell.dll"    $layout
Copy-Item "$here\bin\ImageDietLauncher.exe"  $layout
Copy-Item "$here\assets\Square44x44Logo.png","$here\assets\Square150x150Logo.png","$here\assets\StoreLogo.png" "$layout\assets"

# 3) 패키지 생성
$out = Join-Path $here 'out'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$msix = Join-Path $out 'ImageDietShell.msix'
if (Test-Path $msix) { Remove-Item $msix -Force }
& "$kit\makeappx.exe" pack /d $layout /p $msix /o
if ($LASTEXITCODE -ne 0) { throw "makeappx 실패" }

# 4) 서명 인증서 확보 (CurrentUser\My, 없으면 생성)
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $subject } | Select-Object -First 1
if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type Custom -Subject $subject `
        -KeyUsage DigitalSignature -FriendlyName 'ImageDiet Dev Cert' `
        -CertStoreLocation 'Cert:\CurrentUser\My' `
        -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}')
}
# 공개 인증서 내보내기 (install.ps1이 신뢰 등록에 사용)
$cerPath = Join-Path $out 'ImageDiet.cer'
Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null

# 로컬 신뢰 등록 (개인 게시자 인증서를 신뢰된 사용자로 등록; 대화형 확인 없이 가능)
# 참고: CurrentUser\Root(신뢰된 루트)에 대한 등록은 Windows가 대화형 확인 대화상자를
# 강제하므로(비대화형 빌드 세션에서는 완료 불가) 여기서는 시도하지 않는다.
# 실제 설치 대상 PC에서의 신뢰 등록은 Task 5의 install.ps1이 수행한다.
Import-Certificate -FilePath $cerPath -CertStoreLocation Cert:\CurrentUser\TrustedPeople | Out-Null

# 5) 서명
& "$kit\signtool.exe" sign /fd SHA256 /sha1 $cert.Thumbprint $msix
if ($LASTEXITCODE -ne 0) { throw "signtool 서명 실패" }
& "$kit\signtool.exe" verify /pa $msix
Write-Host "빌드 완료: $msix"
