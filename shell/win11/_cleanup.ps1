# 이전 설치 흔적을 모두 제거 (무충돌 재설치의 핵심). Explorer 재시작은 호출자가 담당.
$ErrorActionPreference = 'SilentlyContinue'
$PkgName = 'ImageDiet.ShellExtension'
$Subject = 'CN=ImageDiet Dev'

# 1) 패키지 제거 (고정 이름이라 항상 이 하나만 존재)
Get-AppxPackage -Name $PkgName | Remove-AppxPackage

# 2) 신뢰 저장소의 인증서 제거 (Subject로 식별, 중복 방지)
#    - LocalMachine\Root / TrustedPeople: install.ps1이 등록하는 신뢰 위치
#    - CurrentUser\TrustedPeople: build.ps1이 등록하는 신뢰 위치
#    - CurrentUser\My: build.ps1이 서명에 사용하는 원본 인증서 (제거해도 다음 build.ps1이 재생성)
foreach ($store in 'Cert:\LocalMachine\Root', 'Cert:\LocalMachine\TrustedPeople', 'Cert:\CurrentUser\TrustedPeople', 'Cert:\CurrentUser\My') {
    Get-ChildItem $store -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $Subject } | Remove-Item -Force -ErrorAction SilentlyContinue
}

# 3) 런타임 설정 키 제거
Remove-Item 'HKCU:\Software\ImageDiet' -Recurse -Force -ErrorAction SilentlyContinue

# 4) legacy(.bat) 우클릭 항목 제거 — 첫화면/더보기 중복 방지
foreach ($ext in '.jpg', '.jpeg', '.png', '.webp', '.bmp') {
    Remove-Item "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\ImageDiet" -Recurse -Force -ErrorAction SilentlyContinue
}
