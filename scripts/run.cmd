@echo off
REM Windows wrapper around run.ps1 — bypasses ExecutionPolicy on default Win10/11.
REM Usage: .\scripts\run.cmd  [-Rebuild]  [-Help]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
