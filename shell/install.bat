@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

rem 이 스크립트가 있는 폴더
set "HERE=%~dp0"
set "GUI=%HERE%compress_gui.pyw"

rem pythonw.exe 탐지: py 런처 우선, 없으면 where, 없으면 기본 경로
set "PYW="
for /f "delims=" %%p in ('py -3 -c "import os,sys;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do (
    if not defined PYW if exist "%%p" set "PYW=%%p"
)
if not defined PYW (
    for /f "delims=" %%p in ('where pythonw.exe 2^>nul') do (
        if not defined PYW set "PYW=%%p"
    )
)
if not defined PYW (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" (
        set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    )
)
if not defined PYW (
    echo pythonw.exe 를 찾을 수 없습니다. Python 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo 엔진: "%PYW%"
echo 스크립트: "%GUI%"

set "MENU=이미지 다이어트로 압축"
for %%E in (.jpg .jpeg .png .webp .bmp) do (
    set "KEY=HKCU\Software\Classes\SystemFileAssociations\%%E\shell\ImageDiet"
    reg add "!KEY!" /ve /d "!MENU!" /f >nul
    reg add "!KEY!" /v Icon /d "\"%HERE%assets\imagediet.ico\"" /f >nul
    reg add "!KEY!" /v MultiSelectModel /d "Player" /f >nul
    reg add "!KEY!\command" /ve /d "\"%PYW%\" \"%GUI%\" \"%%1\"" /f >nul
)
echo 완료. 이미지 우클릭 메뉴에 "!MENU!" 가 추가되었습니다.
pause
