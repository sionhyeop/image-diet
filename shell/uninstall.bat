@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

rem install.bat 으로 등록한 우클릭 메뉴 항목을 제거합니다.
set "MENU=이미지 다이어트로 압축"
for %%E in (.jpg .jpeg .png .webp .bmp) do (
    reg delete "HKCU\Software\Classes\SystemFileAssociations\%%E\shell\ImageDiet" /f >nul 2>&1
)
echo 완료. 우클릭 메뉴에서 "!MENU!" 항목이 제거되었습니다.
pause
