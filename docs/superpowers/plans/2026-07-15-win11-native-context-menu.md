# Win11 네이티브 우클릭 메뉴 + 아이콘 + 창 다듬기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows 11 우클릭 첫 화면에 아이콘과 함께 "이미지 다이어트로 압축"을 띄우고(셸 확장 DLL), 압축 창을 크롬 팝업풍으로 다듬는다. 압축 엔진·GUI 기능은 불변.

**Architecture:** C++/WRL로 `IExplorerCommand` 셸 확장 DLL을 만들어 **자체 완결형 MSIX**(DLL+스텁 exe+아이콘 포함)로 포장·자체 서명·등록한다. DLL은 얇은 껍데기로, 클릭 시 선택 파일을 모아 `pythonw.exe compress_gui.pyw <files>`를 실행한다. pythonw·GUI 스크립트·아이콘의 실제 경로는 install.ps1이 `HKCU\Software\ImageDiet`에 써 넣고 DLL이 런타임에 읽는다(폴더 이동에 강하고, 패키지를 경로에 독립적으로 만듦). 설치는 "초기화 후 설치"라 몇 번 반복해도 무충돌.

**Tech Stack:** C++17 (WRL, Windows SDK 10.0.26100), MSBuild (VS 2026 Community), makeappx/signtool, PowerShell(관리자), Python/Tkinter, Pillow.

## Global Constraints

이 값들은 **모든 파일에서 정확히 동일한 고정 상수**여야 한다(무충돌 재설치의 핵심). 재빌드·재설치해도 절대 바뀌지 않는다:

- 패키지 Identity Name: `ImageDiet.ShellExtension`
- Publisher / 인증서 Subject: `CN=ImageDiet Dev`  (매니페스트 Publisher == 인증서 Subject, 불일치 시 등록 실패)
- 패키지 Version: `1.0.0.0`
- COM CLSID (매니페스트·C++ 양쪽 동일): `B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47`
- Verb Id: `ImageDiet`
- 메뉴 제목: `이미지 다이어트로 압축`
- 대상 확장자: `.jpg .jpeg .png .webp .bmp`
- 런타임 설정 레지스트리 키: `HKCU\Software\ImageDiet` (값: `Pythonw`, `GuiScript`, `IconPath`)
- 신규 파일은 `shell/win11/` 아래. 기존 `shell/compress.py`, `shell/compress_gui.pyw`는 재사용(엔진 미변경).
- 기존 legacy `shell/install.bat`·`shell/uninstall.reg`는 삭제하지 않고 유지. win11 설치 시 legacy 우클릭 항목만 제거해 중복 방지.
- 빌드 도구 경로:
  - MSBuild: `C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe`
  - makeappx/signtool: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\`
  - Windows Python: `C:\Users\sanghyeop\AppData\Local\Programs\Python\Python313\`
- WSL에서 Windows 빌드는 `cmd.exe /c` 경유. 파이썬 테스트는 WSL `python3`.

> **정직한 리스크:** Task 3~5(C++/MSIX/등록)는 매니페스트 정합성·인증서 신뢰·Explorer 캐시 때문에 한 번에 안 될 수 있다. 각 태스크에 디버깅 지침을 넣었고, 실제 메뉴 노출은 Windows 수동 확인이다.

---

### Task 1: 압축 창 크롬 팝업풍으로 다듬기 (`compress_gui.pyw`)

셸 확장과 독립적. 기능(목표 용량 + 형식, 일괄 처리, 설정 저장, 엔진 호출)은 그대로 두고 UI만 교체. 크롬 익스텐션 팝업 느낌: 컴팩트·흰 카드·강조 버튼·진행바·다크모드 자동.

**Files:**
- Modify(전면 UI 교체): `shell/compress_gui.pyw`
- 검증: `python3 -m py_compile` + Windows 수동 시각 확인

**Interfaces:**
- Consumes: `compress.compress_image(src_path, target_kb, out_format) -> dict` (기존, 불변)
- Produces: 진입점 불변 — `pythonw compress_gui.pyw <files...>`. 설정 파일 `%APPDATA%\image-diet-shell\settings.json` 스키마 불변(`target_kb`,`out_format`).

- [ ] **Step 1: 새 UI로 compress_gui.pyw 교체**

기존 로직(argv 파싱, load/save_settings, 스레드 압축, compress_image 호출)은 유지하되 위젯 구성을 아래로 교체. 크롬 팝업 톤(강조색 `#1a73e8`, 카드, 다크모드 감지):

```python
"""이미지 다이어트 — 탐색기 우클릭용 팝업 창 (크롬 익스텐션 톤).
사용법: pythonw compress_gui.pyw <이미지경로> [<이미지경로> ...]"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compress  # noqa: E402

FORMATS = [("자동 (WebP)", "auto"), ("WebP", "webp"),
           ("JPEG", "jpeg"), ("PNG", "png")]
_CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                        "image-diet-shell")
_CFG_PATH = os.path.join(_CFG_DIR, "settings.json")


def load_settings():
    valid = {v for _, v in FORMATS}
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            d = json.load(f)
            fmt = str(d.get("out_format", "auto"))
            if fmt not in valid:
                fmt = "auto"
            return int(d.get("target_kb", 200)), fmt
    except Exception:
        return 200, "auto"


def save_settings(target_kb, out_format):
    try:
        os.makedirs(_CFG_DIR, exist_ok=True)
        with open(_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump({"target_kb": target_kb, "out_format": out_format}, f)
    except Exception:
        pass


def _is_dark():
    """Windows 앱 테마: AppsUseLightTheme=0 이면 다크."""
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return v == 0
    except Exception:
        return False


# 색 팔레트 (라이트/다크)
def _palette(dark):
    if dark:
        return dict(bg="#202124", card="#292a2d", fg="#e8eaed",
                    sub="#9aa0a6", border="#3c4043", accent="#8ab4f8",
                    accent_fg="#202124", field="#303134")
    return dict(bg="#f1f3f4", card="#ffffff", fg="#202124",
                sub="#5f6368", border="#dadce0", accent="#1a73e8",
                accent_fg="#ffffff", field="#ffffff")


class App:
    def __init__(self, root, files):
        self.root = root
        self.files = files
        self.running = False
        self.pal = _palette(_is_dark())
        p = self.pal

        root.title("이미지 다이어트")
        root.configure(bg=p["bg"])
        root.resizable(False, False)
        try:
            root.iconbitmap(os.path.join(os.path.dirname(__file__),
                                         "win11", "assets", "imagediet.ico"))
        except Exception:
            pass

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Card.TFrame", background=p["card"])
        style.configure("Card.TLabel", background=p["card"], foreground=p["fg"])
        style.configure("Sub.TLabel", background=p["card"], foreground=p["sub"])
        style.configure("Accent.TButton", background=p["accent"],
                        foreground=p["accent_fg"], borderwidth=0, focusthickness=0,
                        padding=(16, 8), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", p["accent"]), ("pressed", p["accent"])])
        style.configure("Ghost.TButton", background=p["card"], foreground=p["sub"],
                        borderwidth=1, padding=(14, 8))
        style.configure("TCombobox", fieldbackground=p["field"],
                        background=p["field"], foreground=p["fg"])
        style.configure("Diet.Horizontal.TProgressbar",
                        background=p["accent"], troughcolor=p["field"], borderwidth=0)

        # 외곽 여백 + 카드
        outer = tk.Frame(root, bg=p["bg"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.pack(fill="both", expand=True)

        # 헤더 (로고 + 제목)
        header = ttk.Frame(card, style="Card.TFrame")
        header.grid(column=0, row=0, columnspan=3, sticky="w", pady=(0, 14))
        self._logo = None
        try:
            self._logo = tk.PhotoImage(file=os.path.join(
                os.path.dirname(__file__), "win11", "assets", "logo32.png"))
            ttk.Label(header, image=self._logo, style="Card.TLabel").pack(side="left")
        except Exception:
            pass
        ttk.Label(header, text="  이미지 다이어트", style="Card.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(side="left")

        target0, fmt0 = load_settings()
        ttk.Label(card, text=f"파일 {len(files)}개 선택됨", style="Sub.TLabel").grid(
            column=0, row=1, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(card, text="목표 용량", style="Card.TLabel").grid(
            column=0, row=2, sticky="w", pady=4)
        self.kb = tk.StringVar(value=str(target0))
        tk.Entry(card, textvariable=self.kb, width=8, bg=p["field"], fg=p["fg"],
                 relief="flat", highlightthickness=1, highlightbackground=p["border"],
                 insertbackground=p["fg"]).grid(column=1, row=2, sticky="w", pady=4)
        ttk.Label(card, text="KB", style="Sub.TLabel").grid(column=2, row=2, sticky="w")

        ttk.Label(card, text="출력 형식", style="Card.TLabel").grid(
            column=0, row=3, sticky="w", pady=4)
        self.fmt_label = tk.StringVar(value=next(l for l, v in FORMATS if v == fmt0))
        ttk.Combobox(card, textvariable=self.fmt_label, values=[l for l, _ in FORMATS],
                     state="readonly", width=14).grid(
            column=1, row=3, columnspan=2, sticky="w", pady=4)

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.grid(column=0, row=4, columnspan=3, sticky="e", pady=(14, 6))
        ttk.Button(btns, text="취소", style="Ghost.TButton",
                   command=root.destroy).pack(side="right", padx=(8, 0))
        self.go = ttk.Button(btns, text="압축", style="Accent.TButton", command=self.start)
        self.go.pack(side="right")

        self.prog = ttk.Progressbar(card, style="Diet.Horizontal.TProgressbar",
                                    mode="determinate", maximum=len(files))
        self.prog.grid(column=0, row=5, columnspan=3, sticky="we", pady=(6, 6))
        self.status = tk.Text(card, width=40, height=min(8, max(2, len(files))),
                              bg=p["card"], fg=p["fg"], relief="flat",
                              highlightthickness=0, state="disabled", wrap="none")
        self.status.grid(column=0, row=6, columnspan=3, sticky="we")

    def _fmt_value(self):
        return next(v for l, v in FORMATS if l == self.fmt_label.get())

    def log(self, line):
        self.status.configure(state="normal")
        self.status.insert("end", line + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def start(self):
        if self.running:
            return
        try:
            target = int(self.kb.get())
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("이미지 다이어트", "목표 용량은 양의 정수여야 합니다.")
            return
        fmt = self._fmt_value()
        save_settings(target, fmt)
        self.running = True
        self.go.configure(state="disabled")
        self.prog.configure(value=0)
        threading.Thread(target=self._run, args=(target, fmt), daemon=True).start()

    def _run(self, target, fmt):
        for path in self.files:
            name = os.path.basename(path)
            res = compress.compress_image(path, target, fmt)
            if res.get("ok"):
                msg = f"✓ {os.path.basename(res['out_path'])}  {res['size_kb']}KB"
            else:
                msg = f"✗ {name}: {res.get('error', '')[:38]}"
            self.root.after(0, self.log, msg)
            self.root.after(0, lambda: self.prog.step(1))
        self.root.after(0, self.log, "완료")
        self.root.after(0, lambda: self.go.configure(state="normal"))
        self.running = False


def main():
    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if not files:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("이미지 다이어트", "압축할 이미지를 선택한 뒤 우클릭하세요.")
        return
    root = tk.Tk()
    App(root, files)
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 컴파일 확인**

Run: `cd "/mnt/c/dev/2026 soma/downsizing img/shell" && python3 -m py_compile compress_gui.pyw && echo COMPILE_OK`
Expected: `COMPILE_OK`. (로고/아이콘 파일은 Task 2에서 생성 — 없으면 try/except로 무시되므로 지금 컴파일엔 문제없음)

- [ ] **Step 3: 기존 엔진 테스트 회귀 확인**

Run: `cd "/mnt/c/dev/2026 soma/downsizing img/shell" && python3 -m pytest test_compress.py -q && rm -rf __pycache__`
Expected: `10 passed`.

- [ ] **Step 4: Commit**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/compress_gui.pyw
git commit -m "feat(shell): 압축 창 크롬 팝업풍 UI + 다크모드"
```

---

### Task 2: 아이콘 · 패키지 자산 생성 (`shell/win11/make_assets.py`)

저장소 로고 `icon-512.png`에서 메뉴/창 아이콘(.ico)과 MSIX 필수 로고 PNG들을 생성.

**Files:**
- Create: `shell/win11/make_assets.py`
- Create(스크립트 출력): `shell/win11/assets/imagediet.ico`, `logo32.png`, `Square44x44Logo.png`, `Square150x150Logo.png`, `StoreLogo.png`
- 검증: 스크립트 실행 후 파일 존재·크기 확인

**Interfaces:**
- Consumes: 리포지토리 루트 `icon-512.png`
- Produces: 위 자산 파일들(Task 1 GUI가 `logo32.png`/`imagediet.ico`를, Task 3 DLL이 `imagediet.ico`를, Task 4 매니페스트가 Square/Store 로고를 참조)

- [ ] **Step 1: 자산 생성 스크립트 작성**

`shell/win11/make_assets.py`:

```python
"""icon-512.png -> 메뉴 .ico + MSIX 로고 PNG 생성."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SRC = os.path.join(HERE, "..", "..", "icon-512.png")


def main():
    os.makedirs(ASSETS, exist_ok=True)
    src = Image.open(SRC).convert("RGBA")

    # 메뉴/창 아이콘 (.ico, 다중 해상도)
    src.save(os.path.join(ASSETS, "imagediet.ico"),
             sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (256, 256)])

    # 창 헤더 로고 (Tk PhotoImage는 PNG)
    src.resize((32, 32), Image.LANCZOS).save(os.path.join(ASSETS, "logo32.png"))

    # MSIX 필수 로고
    src.resize((44, 44), Image.LANCZOS).save(os.path.join(ASSETS, "Square44x44Logo.png"))
    src.resize((150, 150), Image.LANCZOS).save(os.path.join(ASSETS, "Square150x150Logo.png"))
    src.resize((50, 50), Image.LANCZOS).save(os.path.join(ASSETS, "StoreLogo.png"))
    print("assets written to", ASSETS)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 실행 및 검증**

Run:
```bash
cd "/mnt/c/dev/2026 soma/downsizing img/shell/win11" && python3 make_assets.py && \
python3 -c "import os; a='assets'; [print(f, os.path.getsize(os.path.join(a,f))) for f in ['imagediet.ico','logo32.png','Square44x44Logo.png','Square150x150Logo.png','StoreLogo.png']]"
```
Expected: 5개 파일 모두 존재하고 크기 > 0. `imagediet.ico`는 수 KB.

- [ ] **Step 3: Commit**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/win11/make_assets.py shell/win11/assets
git commit -m "feat(win11): 메뉴 아이콘·MSIX 로고 자산 생성"
```

---

### Task 3: C++ IExplorerCommand DLL + 스텁 exe (`shell/win11/src`, `.vcxproj`)

우클릭 첫 화면 명령을 구현하는 얇은 COM DLL과, MSIX가 요구하는 최소 스텁 exe.

**Files:**
- Create: `shell/win11/src/pch.h`
- Create: `shell/win11/src/ImageDietCommand.h`
- Create: `shell/win11/src/dllmain.cpp`
- Create: `shell/win11/src/ImageDietShell.def`
- Create: `shell/win11/src/stub.cpp`
- Create: `shell/win11/ImageDietShell.vcxproj` (DLL)
- Create: `shell/win11/ImageDietLauncher.vcxproj` (스텁 exe)
- 검증: MSBuild로 두 프로젝트 컴파일 성공

**Interfaces:**
- Consumes: 런타임에 `HKCU\Software\ImageDiet` 값 `Pythonw`,`GuiScript`,`IconPath`(Task 5 install.ps1이 씀). CLSID는 Global Constraints 값.
- Produces: `ImageDietShell.dll`(CLSID `B7F5A2E1-...` 노출), `ImageDietLauncher.exe`(빈 스텁). Task 4 매니페스트가 참조.

- [ ] **Step 1: C++ 소스 작성**

`shell/win11/src/pch.h`:

```cpp
#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlobj_core.h>
#include <shobjidl_core.h>
#include <shlwapi.h>
#include <wrl/module.h>
#include <wrl/implements.h>
#include <wrl/client.h>
#include <string>
#include <vector>
```

`shell/win11/src/ImageDietCommand.h`:

```cpp
#pragma once
#include "pch.h"
using namespace Microsoft::WRL;

// 런타임 설정 레지스트리에서 값 읽기
inline std::wstring RegRead(const wchar_t* name)
{
    HKEY hk{};
    std::wstring result;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\ImageDiet", 0, KEY_READ, &hk) == ERROR_SUCCESS)
    {
        wchar_t buf[1024]; DWORD cb = sizeof(buf); DWORD type = 0;
        if (RegQueryValueExW(hk, name, nullptr, &type, reinterpret_cast<LPBYTE>(buf), &cb) == ERROR_SUCCESS
            && type == REG_SZ)
        {
            result.assign(buf, cb / sizeof(wchar_t));
            if (!result.empty() && result.back() == L'\0') result.pop_back();
        }
        RegCloseKey(hk);
    }
    return result;
}

class __declspec(uuid("B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47"))
ImageDietCommand : public RuntimeClass<RuntimeClassFlags<ClassicCom>, IExplorerCommand>
{
public:
    IFACEMETHODIMP GetTitle(IShellItemArray*, PWSTR* name) override
    {
        return SHStrDupW(L"이미지 다이어트로 압축", name);
    }
    IFACEMETHODIMP GetIcon(IShellItemArray*, PWSTR* icon) override
    {
        std::wstring path = RegRead(L"IconPath");
        if (path.empty()) { *icon = nullptr; return E_NOTIMPL; }
        return SHStrDupW(path.c_str(), icon);
    }
    IFACEMETHODIMP GetToolTip(IShellItemArray*, PWSTR* infoTip) override
    {
        *infoTip = nullptr; return E_NOTIMPL;
    }
    IFACEMETHODIMP GetCanonicalName(GUID* guid) override { *guid = GUID_NULL; return S_OK; }
    IFACEMETHODIMP GetState(IShellItemArray*, BOOL, EXPCMDSTATE* state) override
    {
        *state = ECS_ENABLED; return S_OK;
    }
    IFACEMETHODIMP GetFlags(EXPCMDFLAGS* flags) override { *flags = ECF_DEFAULT; return S_OK; }
    IFACEMETHODIMP EnumSubCommands(IEnumExplorerCommand** ppEnum) override
    {
        *ppEnum = nullptr; return E_NOTIMPL;
    }
    IFACEMETHODIMP Invoke(IShellItemArray* selection, IBindCtx*) noexcept override
    {
        if (!selection) return S_OK;
        std::wstring pythonw = RegRead(L"Pythonw");
        std::wstring script  = RegRead(L"GuiScript");
        if (pythonw.empty() || script.empty())
        {
            MessageBoxW(nullptr,
                L"이미지 다이어트가 올바르게 설치되지 않았습니다.\ninstall.ps1을 다시 실행하세요.",
                L"이미지 다이어트", MB_ICONERROR);
            return S_OK;
        }
        std::wstring cmd = L"\"" + pythonw + L"\" \"" + script + L"\"";
        DWORD count = 0; selection->GetCount(&count);
        for (DWORD i = 0; i < count; ++i)
        {
            ComPtr<IShellItem> item;
            if (SUCCEEDED(selection->GetItemAt(i, &item)))
            {
                PWSTR p = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &p)))
                {
                    cmd += L" \""; cmd += p; cmd += L"\"";
                    CoTaskMemFree(p);
                }
            }
        }
        std::vector<wchar_t> buf(cmd.begin(), cmd.end()); buf.push_back(0);
        STARTUPINFOW si{ sizeof(si) };
        PROCESS_INFORMATION pi{};
        if (CreateProcessW(nullptr, buf.data(), nullptr, nullptr, FALSE,
                           CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi))
        {
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }
        return S_OK;
    }
};

CoCreatableClass(ImageDietCommand);
```

`shell/win11/src/dllmain.cpp`:

```cpp
#include "pch.h"
#include "ImageDietCommand.h"
using namespace Microsoft::WRL;

BOOL WINAPI DllMain(HINSTANCE hInstance, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
        DisableThreadLibraryCalls(hInstance);
    return TRUE;
}

STDAPI DllCanUnloadNow()
{
    return Module<InProc>::GetModule().GetObjectCount() == 0 ? S_OK : S_FALSE;
}

STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, void** ppv)
{
    return Module<InProc>::GetModule().GetClassObject(rclsid, riid, ppv);
}
```

`shell/win11/src/ImageDietShell.def`:

```
LIBRARY "ImageDietShell"
EXPORTS
    DllGetClassObject   PRIVATE
    DllCanUnloadNow     PRIVATE
```

`shell/win11/src/stub.cpp` (MSIX가 요구하는 최소 exe — 실행되지 않음):

```cpp
#include <windows.h>
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) { return 0; }
```

- [ ] **Step 2: DLL vcxproj 작성**

`shell/win11/ImageDietShell.vcxproj`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <ProjectGuid>{1A2B3C4D-1111-2222-3333-444455556666}</ProjectGuid>
    <RootNamespace>ImageDietShell</RootNamespace>
    <WindowsTargetPlatformVersion>10.0.26100.0</WindowsTargetPlatformVersion>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
  <PropertyGroup Label="Configuration">
    <ConfigurationType>DynamicLibrary</ConfigurationType>
    <PlatformToolset>v143</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
    <UseDebugLibraries>false</UseDebugLibraries>
    <WholeProgramOptimization>true</WholeProgramOptimization>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
  <PropertyGroup>
    <OutDir>$(MSBuildProjectDirectory)\bin\</OutDir>
    <IntDir>$(MSBuildProjectDirectory)\obj\dll\</IntDir>
    <TargetName>ImageDietShell</TargetName>
  </PropertyGroup>
  <ItemDefinitionGroup>
    <ClCompile>
      <LanguageStandard>stdcpp17</LanguageStandard>
      <PreprocessorDefinitions>_WINDOWS;_USRDLL;UNICODE;_UNICODE;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <RuntimeLibrary>MultiThreaded</RuntimeLibrary>
    </ClCompile>
    <Link>
      <SubSystem>Windows</SubSystem>
      <ModuleDefinitionFile>src\ImageDietShell.def</ModuleDefinitionFile>
      <AdditionalDependencies>shlwapi.lib;runtimeobject.lib;%(AdditionalDependencies)</AdditionalDependencies>
    </Link>
  </ItemDefinitionGroup>
  <ItemGroup>
    <ClCompile Include="src\dllmain.cpp" />
  </ItemGroup>
  <ItemGroup>
    <ClInclude Include="src\pch.h" />
    <ClInclude Include="src\ImageDietCommand.h" />
  </ItemGroup>
  <ItemGroup>
    <None Include="src\ImageDietShell.def" />
  </ItemGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
</Project>
```

- [ ] **Step 3: 스텁 exe vcxproj 작성**

`shell/win11/ImageDietLauncher.vcxproj`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <ProjectGuid>{1A2B3C4D-7777-8888-9999-AAAABBBBCCCC}</ProjectGuid>
    <RootNamespace>ImageDietLauncher</RootNamespace>
    <WindowsTargetPlatformVersion>10.0.26100.0</WindowsTargetPlatformVersion>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
  <PropertyGroup Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <PlatformToolset>v143</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
    <UseDebugLibraries>false</UseDebugLibraries>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
  <PropertyGroup>
    <OutDir>$(MSBuildProjectDirectory)\bin\</OutDir>
    <IntDir>$(MSBuildProjectDirectory)\obj\exe\</IntDir>
    <TargetName>ImageDietLauncher</TargetName>
  </PropertyGroup>
  <ItemDefinitionGroup>
    <ClCompile>
      <LanguageStandard>stdcpp17</LanguageStandard>
      <RuntimeLibrary>MultiThreaded</RuntimeLibrary>
    </ClCompile>
    <Link><SubSystem>Windows</SubSystem></Link>
  </ItemDefinitionGroup>
  <ItemGroup>
    <ClCompile Include="src\stub.cpp" />
  </ItemGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
</Project>
```

- [ ] **Step 4: 빌드 확인 (WSL → cmd.exe)**

Run:
```bash
MSB='C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe'
cd "/mnt/c/dev/2026 soma/downsizing img/shell/win11"
cmd.exe /c "\"$MSB\" ImageDietShell.vcxproj /p:Configuration=Release /p:Platform=x64 /v:m" 2>&1 | tail -8
cmd.exe /c "\"$MSB\" ImageDietLauncher.vcxproj /p:Configuration=Release /p:Platform=x64 /v:m" 2>&1 | tail -8
ls -la bin/ImageDietShell.dll bin/ImageDietLauncher.exe
```
Expected: `Build succeeded` 두 번, `bin/ImageDietShell.dll`·`bin/ImageDietLauncher.exe` 생성.

**디버깅 지침(실패 시):** 헤더 누락이면 `pch.h`의 include 순서 확인. `IExplorerCommand` 미해결이면 `shobjidl_core.h` 포함 확인. `SHStrDupW` 링크 에러면 `shlwapi.lib` 확인. def 관련 경고는 무시 가능. 컴파일러/툴셋 버전(v143)이 안 맞으면 설치된 최신 v14x로 조정.

- [ ] **Step 5: obj 산출물 무시 + Commit**

`shell/win11/.gitignore` 생성:
```
obj/
bin/
```

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/win11/src shell/win11/ImageDietShell.vcxproj shell/win11/ImageDietLauncher.vcxproj shell/win11/.gitignore
git commit -m "feat(win11): IExplorerCommand 셸 확장 DLL + 스텁 exe"
```

---

### Task 4: MSIX 매니페스트 + 빌드/서명 스크립트 (`AppxManifest.xml`, `build.ps1`)

DLL·스텁·아이콘을 자체 완결형 MSIX로 포장하고 자체 서명한다.

**Files:**
- Create: `shell/win11/package/AppxManifest.xml`
- Create: `shell/win11/build.ps1`
- 검증: `build.ps1` 실행 → 서명된 `out/ImageDietShell.msix` + `out/ImageDiet.cer` 생성, `signtool verify` 통과

**Interfaces:**
- Consumes: Task 2 자산(Square/Store 로고, imagediet.ico), Task 3 산출물(`bin/ImageDietShell.dll`, `bin/ImageDietLauncher.exe`). Global Constraints의 Name/Publisher/CLSID/Version.
- Produces: `out/ImageDietShell.msix`(서명됨), `out/ImageDiet.cer`(공개 인증서). Task 5 install.ps1이 소비.

- [ ] **Step 1: AppxManifest.xml 작성**

`shell/win11/package/AppxManifest.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  xmlns:com="http://schemas.microsoft.com/appx/manifest/com/windows10"
  xmlns:desktop4="http://schemas.microsoft.com/appx/manifest/desktop/windows10/4"
  xmlns:desktop5="http://schemas.microsoft.com/appx/manifest/desktop/windows10/5"
  IgnorableNamespaces="uap rescap com desktop4 desktop5">

  <Identity Name="ImageDiet.ShellExtension"
            Publisher="CN=ImageDiet Dev"
            Version="1.0.0.0"
            ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>Image Diet Shell</DisplayName>
    <PublisherDisplayName>ImageDiet Dev</PublisherDisplayName>
    <Logo>assets\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-us" />
  </Resources>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>

  <Applications>
    <Application Id="ImageDietShell" Executable="ImageDietLauncher.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="Image Diet Shell"
        Description="탐색기 우클릭 이미지 압축"
        BackgroundColor="transparent"
        Square150x150Logo="assets\Square150x150Logo.png"
        Square44x44Logo="assets\Square44x44Logo.png"
        AppListEntry="none" />
      <Extensions>
        <com:Extension Category="windows.comServer">
          <com:ComServer>
            <com:SurrogateServer DisplayName="Image Diet Command">
              <com:Class Id="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47"
                         Path="ImageDietShell.dll" ThreadingModel="STA" />
            </com:SurrogateServer>
          </com:ComServer>
        </com:Extension>
        <desktop4:Extension Category="windows.fileExplorerContextMenus">
          <desktop4:FileExplorerContextMenus>
            <desktop5:ItemType Type=".jpg">
              <desktop5:Verb Id="ImageDiet" Clsid="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47" />
            </desktop5:ItemType>
            <desktop5:ItemType Type=".jpeg">
              <desktop5:Verb Id="ImageDiet" Clsid="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47" />
            </desktop5:ItemType>
            <desktop5:ItemType Type=".png">
              <desktop5:Verb Id="ImageDiet" Clsid="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47" />
            </desktop5:ItemType>
            <desktop5:ItemType Type=".webp">
              <desktop5:Verb Id="ImageDiet" Clsid="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47" />
            </desktop5:ItemType>
            <desktop5:ItemType Type=".bmp">
              <desktop5:Verb Id="ImageDiet" Clsid="B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47" />
            </desktop5:ItemType>
          </desktop4:FileExplorerContextMenus>
        </desktop4:Extension>
      </Extensions>
    </Application>
  </Applications>
</Package>
```

- [ ] **Step 2: build.ps1 작성**

`shell/win11/build.ps1`:

```powershell
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
Export-Certificate -Cert $cert -FilePath (Join-Path $out 'ImageDiet.cer') -Force | Out-Null

# 5) 서명
& "$kit\signtool.exe" sign /fd SHA256 /sha1 $cert.Thumbprint $msix
if ($LASTEXITCODE -ne 0) { throw "signtool 서명 실패" }
& "$kit\signtool.exe" verify /pa $msix
Write-Host "빌드 완료: $msix"
```

- [ ] **Step 3: 빌드 실행·검증 (WSL → cmd.exe)**

Run:
```bash
cd "/mnt/c/dev/2026 soma/downsizing img/shell/win11"
cmd.exe /c "powershell -NoProfile -ExecutionPolicy Bypass -File build.ps1" 2>&1 | tail -15
ls -la out/ImageDietShell.msix out/ImageDiet.cer
```
Expected: "빌드 완료" + `Successfully verified`, `out/ImageDietShell.msix`·`out/ImageDiet.cer` 생성.

**디버깅 지침(실패 시):** makeappx가 매니페스트 스키마 오류를 내면 네임스페이스 접두사(desktop5 ItemType/Verb) 확인. Publisher(`CN=ImageDiet Dev`)와 인증서 Subject 불일치면 서명은 되나 등록이 실패하므로 정확히 일치시킬 것. `runFullTrust` capability 누락 시 데스크톱 확장 등록 거부됨.

- [ ] **Step 4: out/layout 무시 + Commit**

`shell/win11/.gitignore`에 추가: `out/`, `layout/`.

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/win11/package/AppxManifest.xml shell/win11/build.ps1 shell/win11/.gitignore
git commit -m "feat(win11): MSIX 매니페스트 + 자체서명 빌드 스크립트"
```

---

### Task 5: 설치/삭제 스크립트 — 무충돌 재설치 (`install.ps1`, `uninstall.ps1`, `_cleanup.ps1`)

관리자 권한으로 인증서 신뢰·패키지 등록. **초기화 후 설치**라 반복해도 무충돌. 사용자 최중요 요구.

**Files:**
- Create: `shell/win11/_cleanup.ps1` (공유 제거 로직)
- Create: `shell/win11/install.ps1`
- Create: `shell/win11/uninstall.ps1`
- 검증: 정적 검토 + Windows 관리자 수동 실행(무충돌 반복 테스트는 Task 6 체크리스트)

**Interfaces:**
- Consumes: Task 4 산출물(`out/ImageDietShell.msix`, `out/ImageDiet.cer`), Windows Python(pythonw), `shell/compress_gui.pyw`, `shell/win11/assets/imagediet.ico`. Global Constraints의 이름·경로·확장자.
- Produces: 등록된 셸 확장 + `HKCU\Software\ImageDiet` 설정값.

- [ ] **Step 1: 공유 제거 로직 `_cleanup.ps1` 작성**

```powershell
# 이전 설치 흔적을 모두 제거 (무충돌 재설치의 핵심). Explorer 재시작은 호출자가 담당.
$ErrorActionPreference = 'SilentlyContinue'
$PkgName = 'ImageDiet.ShellExtension'
$Subject = 'CN=ImageDiet Dev'

# 1) 패키지 제거 (고정 이름이라 항상 이 하나만 존재)
Get-AppxPackage -Name $PkgName | Remove-AppxPackage

# 2) 신뢰 저장소의 인증서 제거 (Subject로 식별, 중복 방지)
foreach ($store in 'Cert:\LocalMachine\Root', 'Cert:\LocalMachine\TrustedPeople') {
    Get-ChildItem $store | Where-Object { $_.Subject -eq $Subject } | Remove-Item -Force
}

# 3) 런타임 설정 키 제거
Remove-Item 'HKCU:\Software\ImageDiet' -Recurse -Force

# 4) legacy(.bat) 우클릭 항목 제거 — 첫화면/더보기 중복 방지
foreach ($ext in '.jpg', '.jpeg', '.png', '.webp', '.bmp') {
    Remove-Item "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\ImageDiet" -Recurse -Force
}
```

- [ ] **Step 2: `install.ps1` 작성**

```powershell
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

# 4) 패키지 등록
$msix = Join-Path $here 'out\ImageDietShell.msix'
if (-not (Test-Path $msix)) { throw "out\ImageDietShell.msix 없음. 먼저 build.ps1 실행." }
Add-AppxPackage -Path $msix

# 5) Explorer 재시작으로 메뉴 캐시 갱신
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer
Write-Host "설치 완료. 이미지 우클릭 첫 화면에 '이미지 다이어트로 압축' 이 나타납니다."
```

- [ ] **Step 3: `uninstall.ps1` 작성**

```powershell
#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\_cleanup.ps1"
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer
Write-Host "제거 완료."
```

- [ ] **Step 4: 정적 검토**

읽으며 확인: (a) install이 맨 처음 `_cleanup.ps1`을 호출해 초기화하는가, (b) 패키지 Name·인증서 Subject가 Global Constraints와 정확히 일치하는가, (c) `_cleanup`이 `SilentlyContinue`라 대상이 없어도 안전한가, (d) install/uninstall 둘 다 `#Requires -RunAsAdministrator`인가. (PowerShell 구문 자체는 Windows에서만 실행 가능 — 실제 동작은 Task 6에서.)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/win11/_cleanup.ps1 shell/win11/install.ps1 shell/win11/uninstall.ps1
git commit -m "feat(win11): 무충돌 재설치 install/uninstall 스크립트"
```

---

### Task 6: 문서 + 수동 검증 체크리스트 (`shell/win11/README.md`, 루트 README)

빌드·설치·삭제·문제해결과, **무충돌 재설치**를 포함한 Windows 수동 검증 절차를 남긴다.

**Files:**
- Create: `shell/win11/README.md`
- Modify: `README.md`(루트) — legacy 안내 줄 옆에 첫화면 방식 링크 추가
- 검증: 문서 정확성 + Windows 수동 체크리스트 수행 안내

**Interfaces:**
- Consumes: 앞 태스크 전체.
- Produces: (없음)

- [ ] **Step 1: `shell/win11/README.md` 작성**

```markdown
# 이미지 다이어트 — Win11 첫 화면 우클릭 메뉴

우클릭 **첫 화면**(“더 많은 옵션 표시” 없이)에 아이콘과 함께 “이미지 다이어트로 압축”을 띄웁니다.
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
- “올바르게 설치되지 않았습니다” 대화상자: `HKCU\Software\ImageDiet` 값이 비었을 때 → `install.ps1` 재실행.
- 폴더를 옮겼다면: 옮긴 위치에서 `install.ps1` 재실행(경로 자동 갱신).

## 간단 버전(무관리자)
첫 화면 대신 “더 많은 옵션 표시” 안이면 충분하다면, 상위 폴더의 `../install.bat`(레지스트리 방식, 관리자 불필요)을 쓰세요.
```

- [ ] **Step 2: 루트 README에 링크 추가**

`README.md`의 기존 데스크톱 우클릭 안내 줄
`- **데스크톱 우클릭 압축(Windows)** — ... [`shell/README.md`](shell/README.md) 참고`
바로 다음 줄에 추가:

```markdown
- **Win11 첫 화면 우클릭(선택)** — “더 많은 옵션 표시” 없이 첫 화면에 아이콘과 함께 표시. 빌드·설치는 [`shell/win11/README.md`](shell/win11/README.md) 참고
```

- [ ] **Step 3: Windows 수동 검증 체크리스트 (사용자 수행)**

관리자 PowerShell에서:
1. `install.ps1` → 이미지 우클릭 **첫 화면**에 아이콘+“이미지 다이어트로 압축” 노출 확인.
2. 클릭 → 크롬 팝업풍 창 → 압축 → 원본 옆 `사진1.webp` 생성.
3. 이미지 2~3개 선택 후 클릭 → **한 창**에서 일괄 처리.
4. **무충돌 반복 테스트(최중요):** `install` → `uninstall` → `install` → `install` 반복 후:
   - `Get-AppxPackage ImageDiet.ShellExtension` → **1개만**
   - `Get-ChildItem Cert:\LocalMachine\Root | ? Subject -eq 'CN=ImageDiet Dev'` → **1개만**
   - 우클릭 메뉴 항목 **1개만**(첫 화면/더보기 중복 없음)
5. `uninstall.ps1` → 메뉴에서 항목 사라짐 확인.

- [ ] **Step 4: 엔진 회귀 확인 + Commit**

```bash
cd "/mnt/c/dev/2026 soma/downsizing img/shell" && python3 -m pytest test_compress.py -q && rm -rf __pycache__
cd "/mnt/c/dev/2026 soma/downsizing img"
git add shell/win11/README.md README.md
git commit -m "docs(win11): 첫 화면 메뉴 빌드·설치·무충돌 재설치 문서"
```

---

## Self-Review 결과

- **Spec coverage:** 첫화면 메뉴(Task 3,4,5)·아이콘(Task 2,3,4)·크롬 팝업 UI(Task 1)·무충돌 재설치(Task 5 `_cleanup`+install 초기화, Task 6 반복 테스트)·관리자 설치(Task 5)·legacy 병행+중복 제거(Task 5,6)·엔진 불변(Task 1 회귀 테스트) 모두 태스크로 커버.
- **Placeholder scan:** 코드 스텝은 전부 완전한 코드. C++/MSIX/PS의 검증 불가 영역은 구체 명령+기대결과+디버깅 지침으로 대체(자동 테스트 불가는 명시적 제약).
- **Type/이름 일관성:** CLSID `B7F5A2E1-9C4D-4A3E-8F21-6D0E3C9A5B47`, 패키지 `ImageDiet.ShellExtension`, Subject `CN=ImageDiet Dev`, 레지스트리 `HKCU\Software\ImageDiet`(`Pythonw`/`GuiScript`/`IconPath`)가 C++·매니페스트·PS 전반에서 동일. GUI 진입점·설정 스키마 불변.
- **스펙 대비 의도적 개선:** 스펙의 "스파스 MSIX"를 "자체 완결형 MSIX"로 변경(external-location 제거로 실패 지점↓, 경로는 레지스트리로 주입 → 폴더 이동·무충돌 재설치에 더 유리). 결과·제약은 스펙과 동일.
