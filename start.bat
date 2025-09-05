@echo off
setlocal
REM Wrapper para ejecutar start.ps1 con PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
endlocal

