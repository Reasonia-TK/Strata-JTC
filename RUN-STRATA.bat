@echo off
chcp 65001 >nul
setlocal
title Strata
cd /d "%~dp0"

rem ===== Settings: edit the values below. See docs/UV_SETUP.md. =====
rem MODEL: auto = most recently used; or a config name, e.g. strata-q2_0.json.
rem 未導入のモデルを追加するには ADD-MODEL.bat を実行してください。
if not defined STRATA_MODEL set "STRATA_MODEL=auto"
rem VISION: keep / on / off / gpu / cpu. ON needs an installed encoder.
if not defined STRATA_VISION set "STRATA_VISION=keep"
rem CONTEXT: auto = saved value; or token count, e.g. 32768 / 65536 / 262144.
if not defined STRATA_CONTEXT set "STRATA_CONTEXT=auto"
rem PORT: auto = saved value; or port number, e.g. 8080 / 8081.
if not defined STRATA_PORT set "STRATA_PORT=auto"
rem GPU: auto = saved selection; or 0 / 1 / 0,1. BROWSER: auto / yes / no.
if not defined STRATA_GPU set "STRATA_GPU=auto"
if not defined STRATA_BROWSER set "STRATA_BROWSER=auto"
rem HOST: 127.0.0.1 = this PC. Other addresses require STRATA_API_KEY.
if not defined STRATA_HOST set "STRATA_HOST=127.0.0.1"
rem Optional company proxy/CA (uncomment and edit; certificates stay verified):
rem set "HTTPS_PROXY=http://proxy.example:8080"
rem set "SSL_CERT_FILE=C:\certs\company-ca.pem"
rem ===== End of settings =====

if not exist ".venv\Scripts\python.exe" (
  echo Run START-HERE.bat once to complete setup, then run this file again.
  pause
  exit /b 1
)
call "%~dp0tools\uv-env.bat"
if errorlevel 1 goto failed
"%STRATA_UV_EXE%" run --locked --no-sync --no-dev python tools\launch_strata.py --model "%STRATA_MODEL%" --vision "%STRATA_VISION%" --context "%STRATA_CONTEXT%" --port "%STRATA_PORT%" --gpu "%STRATA_GPU%" --browser "%STRATA_BROWSER%" --host "%STRATA_HOST%" %*
set "STRATA_EXIT=%ERRORLEVEL%"
if not "%STRATA_EXIT%"=="0" pause
exit /b %STRATA_EXIT%

:failed
echo Could not install or find uv. See docs/UV_SETUP.md.
pause
exit /b 1
