#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\_cleanup.ps1"
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer
Write-Host "제거 완료."
