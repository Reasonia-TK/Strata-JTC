@echo off
chcp 65001 >nul
rem 設定変更とセットアップ後の起動。モデルの追加だけなら ADD-MODEL.bat を使用します。
call "%~dp0START-HERE.bat" --setup %*
