@echo off
chcp 65001 >nul
setlocal
title Strata - モデルを追加
cd /d "%~dp0"
echo.
echo 未導入のモデル・サイズを選び、ダウンロードと利用準備を行います。
echo 導入済みのファイルは再利用します。同じモデルを選ぶと設定を変更します。
echo 完了後は RUN-STRATA.bat またはモデル別の run-*.bat で起動できます。
echo.
call "%~dp0START-HERE.bat" --setup --no-start %*
set "STRATA_EXIT=%ERRORLEVEL%"
if not "%STRATA_EXIT%"=="0" exit /b %STRATA_EXIT%
echo.
echo 処理が終了しました。導入済みモデルは RUN-STRATA.bat --list-models で確認できます。
if "%~1"=="" pause
exit /b 0
