# uvでのセットアップとWindowsでの起動

Pythonの依存関係は`pyproject.toml`と`uv.lock`で管理します。`START-HERE.bat`と`setup.sh`はuvで
`.venv`を用意し、必要ならPythonも取得します。uvが見つからなければ、このフォルダーの`.uv`に
インストールします。既存の`.venv`も利用できます。以前のpip用の記録によるインストール省略は行わず、
ロックファイルに合わせます。

## セットアップ

Windowsでは`START-HERE.bat`をダブルクリックします。ターミナルからも実行できます。

```powershell
.\START-HERE.bat --yes --family qwen --model IQ2_XS --vision yes --no-start
# uvが既にある場合:
uv run --locked python setup.py
```

LinuxとmacOSでは`./setup.sh`を実行します。NixOSではuvの管理するPythonを使います。
エンジンのビルドに必要なコンパイラーやGPUドライバーは、Pythonの依存関係とは別に必要です。

依存関係の変更は`uv add PACKAGE`、削除は`uv remove PACKAGE`で行い、`uv.lock`も更新します。
基本パッケージの同期は`uv sync --locked`です。CUDAライブラリはセットアップがバックエンドに合わせて
選びます。手動で指定する場合は次のコマンドを使います。

```powershell
uv sync --locked --inexact --extra cuda13
# 旧世代GPUのCUDA 12エンジン:
uv sync --locked --inexact --extra cuda12
```

`--inexact`は別のモデルで使うCUDAライブラリやROCmの追加パッケージを残します。
LinuxのROCmはGPUごとにAMDの配布先が異なるため、既存のバージョン選択を保ち、`uv pip install`で
対象の`.venv`に入れます。基本パッケージとCUDAのバージョンは`uv.lock`に記録します。

`requirements.txt`は互換性のための生成物です。手で編集せず、依存関係の変更後に再生成します。

```powershell
uv export --locked --format requirements-txt --no-hashes --no-emit-project --no-dev --output-file requirements.txt
```

## 別のモデルを後から追加する

初回セットアップで選ばなかったモデルは、`ADD-MODEL.bat`をダブルクリックして追加します。
モデルの種類、サイズ、コンテキスト長、Visionを選ぶと、ダウンロードと利用準備を行います。
完了後はサーバーを起動せずに終了します。導入済みの共通ファイルは再利用します。
同じモデル・サイズを選ぶと、そのモデルの設定変更になります。

モデルとサイズを指定する場合は、次のように実行できます。

```powershell
.\ADD-MODEL.bat --family qwen --model IQ3_S
.\ADD-MODEL.bat --family swift --model IQ2_XS
# 推奨設定を使い、質問なしで追加:
.\ADD-MODEL.bat --family coder --yes
# GLMを追加（量子化をメニューで選ぶ）:
.\ADD-MODEL.bat --family glm53
```

Linux/macOSでは`./setup.sh --setup --no-start`を実行します。
追加後は`RUN-STRATA.bat --list-models`で設定ファイル名を確認し、`STRATA_MODEL`に指定します。

```powershell
.\RUN-STRATA.bat --model swift-iq2_xs
```

## セットアップ後の起動

`RUN-STRATA.bat`をダブルクリックします。先頭の設定欄の値を編集できます。
セットアップで作成される`run-<model>.bat`にも同じ設定欄があります。

| 設定 | 値と意味 |
| --- | --- |
| `STRATA_MODEL` | `auto`で最近起動したモデル。`strata-iq2_xs.json`、`iq2_xs`、設定ファイルのフルパスも指定可能 |
| `STRATA_VISION` | `keep`で保存済み設定、`on`で有効、`off`で無効、`gpu` / `cpu`でencoderの実行先を指定 |
| `STRATA_CONTEXT` | `auto`で保存済み設定。`32768`、`65536`、`262144`などトークン数を指定 |
| `STRATA_PORT` | `auto`で保存済み設定。`8080`、`8081`など1〜65535の番号を指定 |
| `STRATA_GPU` | `auto`で保存済み選択。`0`、`1`、`0,1`など |
| `STRATA_GPU_LAYERS` | GLM専用。`auto`で保存値、`all`または0以上のレイヤー数。`0`でCPU計算 |
| `STRATA_CPU_MOE` | GLM専用。`auto`で保存値、`on`でMoEのCPU計算、`off`でCPU固定を解除 |
| `STRATA_BROWSER` | `auto`で保存済み設定。`yes`でブラウザーを開く、`no`で開かない |
| `STRATA_HOST` | 通常は`127.0.0.1`。別のアドレスには`STRATA_API_KEY`または保存済みAPIキーが必要 |

画像を無効にし、コンテキスト65536、ポート8081で起動する設定例:

```bat
if not defined STRATA_VISION set "STRATA_VISION=off"
if not defined STRATA_CONTEXT set "STRATA_CONTEXT=65536"
if not defined STRATA_PORT set "STRATA_PORT=8081"
```

設定は今回の起動に適用され、モデルのJSON設定は書き換えません。環境変数を指定している場合は
その値を優先します。コマンドライン引数はbat内の値より優先します。

```powershell
.\RUN-STRATA.bat --list-models
.\RUN-STRATA.bat --model iq2_xs --vision off --context 65536 --port 8081 --dry-run
.\RUN-STRATA.bat --model iq2_xs --vision on --port 8081
```

`--dry-run`はモデルを読み込まず、適用する設定を表示します。
まだインストールしていないモデルは先に`ADD-MODEL.bat`で導入してください。
VisionをONにするには、そのモデルのencoderを先にセットアップする必要があります。
GLMの導入はテキスト専用で、Visionは`keep`または`off`です。[量子化別の容量とGLMの手順](GLM_SETUP.md)を参照してください。
未導入なら`START-HERE.bat --setup --vision yes`を実行して対象モデルを選んでください。
GPUで動くencoderを用意していない場合は`cpu`を使います。対応するencoderはGPUとバックエンドによります。

コンテキストを増やすと必要なメモリーも増えます。この起動方法は保存済みのRAM/VRAM予算やKV設定を
自動で再調整しません。大きく変更する場合は`SETUP.bat`で設定を作り直してください。
Flash-Nextの学習時の262144トークンを超える指定ではRoPE拡張と倍率を適用します。既存の拡張方法が
あればそれを使い、倍率は今回のコンテキスト長から再計算します。

## 会社のLAN、プロキシ、CA証明書

Hugging Faceのモデルとvision encoderは`huggingface-hub`の`hf_hub_download`で取得します。
固定リビジョン、ミラーの`HF_ENDPOINT`、既存のSHA-256検証を維持します。完了済みファイルは再取得せず、
中断した取得はモデルの保存先にある`.cache/strata-hub`から再開します。従来の`.part`もサーバーの
メタデータを確認して引き継ぎます。

uvはOSの信頼済み証明書を使う設定です。Python側も`truststore`でOSの証明書ストアを利用し、
公開CA証明書と併用します。会社のCAがOSに登録済みなら、そのCAを利用できます。
TLSの証明書検証とホスト名の検証は有効のままです。

プロキシが必要なら次のように設定します。CAがOSに未登録の場合は、会社から提供されたPEM形式の
CA証明書を指定します。

```powershell
$env:HTTPS_PROXY = "http://proxy.example:8080"
$env:HTTP_PROXY = $env:HTTPS_PROXY
$env:NO_PROXY = "localhost,127.0.0.1"
$env:SSL_CERT_FILE = "C:\certs\company-ca.pem"
.\START-HERE.bat
```

batに保存する場合は、実行部分より前に次の設定を追加します。

```bat
set "HTTPS_PROXY=http://proxy.example:8080"
set "HTTP_PROXY=%HTTPS_PROXY%"
set "NO_PROXY=localhost,127.0.0.1"
set "SSL_CERT_FILE=C:\certs\company-ca.pem"
```

Python側は`REQUESTS_CA_BUNDLE`、`CURL_CA_BUNDLE`、`SSL_CERT_DIR`にも対応します。
uvと共通に設定する場合は`SSL_CERT_FILE`を使います。会社で許可されている接続先やプロキシ認証も必要です。
会社のCAの未登録や、接続先の遮断そのものを自動で解消するものではありません。

HubのHTTPクライアントに同じ証明書設定を使うため、セットアップは`HF_HUB_DISABLE_XET=1`を既定にします。
中断した大容量モデルの取得を再開できるよう、`huggingface-hub`は追記・HTTP Rangeを確認した1.15.0に固定しています。
Xetを利用する場合は事前に`HF_HUB_DISABLE_XET=0`を指定してください。その場合はXet側の証明書と
プロキシの設定も必要です。MTP取得は必要な範囲だけを読む方式を保ち、同じTLS設定を利用します。

公式資料: [Hugging Faceのファイル取得](https://huggingface.co/docs/huggingface_hub/package_reference/file_download)、
[HTTPクライアントの設定](https://huggingface.co/docs/huggingface_hub/package_reference/utilities)、
[uvのTLS証明書](https://docs.astral.sh/uv/concepts/authentication/certificates/)。
