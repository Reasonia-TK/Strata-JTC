@echo off
chcp 65001 >nul
rem Strata for Windows: uv manages Python and .venv; first run installs the model.
setlocal
title Strata
cd /d "%~dp0"
call "%~dp0tools\uv-env.bat"
if errorlevel 1 goto failed
"%STRATA_UV_EXE%" run --locked --no-dev python setup.py %*
set "STRATA_EXIT=%ERRORLEVEL%"
if not "%STRATA_EXIT%"=="0" pause
exit /b %STRATA_EXIT%

:failed
echo Could not install uv. Check your proxy and trusted certificates.
echo Install uv from https://docs.astral.sh/uv/getting-started/installation/ then retry.
pause
exit /b 1
