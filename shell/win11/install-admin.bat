@echo off
rem 이미지 다이어트 Win11 첫 화면 메뉴 설치
rem 더블클릭하면 관리자 권한으로 자동 승격 후 install.ps1 실행
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
