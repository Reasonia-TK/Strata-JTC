@echo off
chcp 65001 >nul
setlocal
title Strata
cd /d "%~dp0"

rem ===== 起動設定: 下の値を変更できます。詳細は docs/UV_SETUP.md。 =====
rem MODEL: auto は最近起動したモデル。例: q2_0、glm53-ud-iq1_s。
rem ADD-MODEL.bat
if not defined STRATA_MODEL set "STRATA_MODEL=auto"
rem VISION: keep / on / off / gpu / cpu。on には導入済みencoderが必要。GLMはkeep/off。
if not defined STRATA_VISION set "STRATA_VISION=keep"
rem CONTEXT: auto は保存値。例: 2048 / 32768 / 65536 / 262144。
if not defined STRATA_CONTEXT set "STRATA_CONTEXT=auto"
rem PORT: auto は保存値。例: 8080 / 8081。
if not defined STRATA_PORT set "STRATA_PORT=auto"
rem GPU: auto は保存値。例: 0 / 1 / 0,1。BROWSER: auto / yes / no。
if not defined STRATA_GPU set "STRATA_GPU=auto"
rem GLM専用: GPU_LAYERS は auto（保存値）/ all / レイヤー数（0でCPU）。
if not defined STRATA_GPU_LAYERS set "STRATA_GPU_LAYERS=auto"
rem GLM専用: CPU_MOE は auto（保存値）/ on / off。onでMoEの重みをCPUで計算。
if not defined STRATA_CPU_MOE set "STRATA_CPU_MOE=auto"
if not defined STRATA_BROWSER set "STRATA_BROWSER=auto"
rem HOST: 127.0.0.1 はこのPCのみ。別のアドレスにはSTRATA_API_KEYが必要。
if not defined STRATA_HOST set "STRATA_HOST=127.0.0.1"
rem 会社のプロキシ/CAを使う場合は、以下のremを外して変更してください。
rem set "HTTPS_PROXY=http://proxy.example:8080"
rem set "SSL_CERT_FILE=C:\certs\company-ca.pem"
rem ===== 起動設定ここまで =====

if not exist ".venv\Scripts\python.exe" (
  echo 最初に START-HERE.bat でセットアップを完了してください。
  pause
  exit /b 1
)
call "%~dp0tools\uv-env.bat"
if errorlevel 1 goto failed
"%STRATA_UV_EXE%" run --locked --no-sync --no-dev python tools\launch_strata.py --model "%STRATA_MODEL%" --vision "%STRATA_VISION%" --context "%STRATA_CONTEXT%" --port "%STRATA_PORT%" --gpu "%STRATA_GPU%" --gpu-layers "%STRATA_GPU_LAYERS%" --cpu-moe "%STRATA_CPU_MOE%" --browser "%STRATA_BROWSER%" --host "%STRATA_HOST%" %*
set "STRATA_EXIT=%ERRORLEVEL%"
if not "%STRATA_EXIT%"=="0" pause
exit /b %STRATA_EXIT%

:failed
echo uvを用意できませんでした。docs/UV_SETUP.md を確認してください。
pause
exit /b 1
