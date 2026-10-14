@echo off
rem Called by Strata's launchers. Install uv locally only when it is missing.
set "STRATA_UV_EXE="
for /f "delims=" %%U in ('where uv 2^>nul') do if not defined STRATA_UV_EXE set "STRATA_UV_EXE=%%U"
if not defined STRATA_UV_EXE if exist "%~dp0..\.uv\uv.exe" set "STRATA_UV_EXE=%~dp0..\.uv\uv.exe"
if not defined STRATA_UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "STRATA_UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if defined STRATA_UV_EXE exit /b 0
echo Installing uv in this Strata folder ...
set "STRATA_UV_INSTALL_DIR=%~dp0..\.uv"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $env:UV_INSTALL_DIR=[IO.Path]::GetFullPath($env:STRATA_UV_INSTALL_DIR); $env:UV_NO_MODIFY_PATH='1'; Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression"
if errorlevel 1 exit /b 1
if not exist "%~dp0..\.uv\uv.exe" exit /b 1
set "STRATA_UV_EXE=%~dp0..\.uv\uv.exe"
exit /b 0
