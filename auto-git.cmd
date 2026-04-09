@echo off
REM Auto-GIT global launcher — works from any directory without activating env
REM Place this file in a directory on your PATH, or add D:\Projects\auto-git to PATH

REM Force UTF-8 console for Unicode banner
chcp 65001 >nul 2>&1

if exist "D:\.conda\envs\auto-git\Scripts\auto-git.exe" (
    "D:\.conda\envs\auto-git\Scripts\auto-git.exe" %*
    exit /b %ERRORLEVEL%
)

REM Fallback: run via python
"D:\.conda\envs\auto-git\python.exe" "D:\Projects\auto-git\cli_entry.py" %*
