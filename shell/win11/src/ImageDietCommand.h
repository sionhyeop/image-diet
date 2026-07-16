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
