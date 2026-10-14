<h1 align="center">Strata-jtc</h1>

<p align="center"><b>大規模なAIモデルを、自分のPCで動かす</b><br>
NVIDIA / AMD GPUとシステムRAMを利用 · Windows / Linux · オープンソース</p>

Strata-jtcは、[Strata](https://github.com/Niko1221/Strata)をもとに、ローカルPCで
**[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)**とその派生モデルを動かすプロジェクトです。
チャット、コード作成、画像の読み取り、各種アプリやコーディングエージェントとの連携に対応します。
推論は自分のPCで行います。
**[GLM-5.3-Flash](https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF)**も、専用のllama.cppエンジンを使って
量子化レベルを選んで追加できます（[導入手順と必要な容量](docs/GLM_SETUP.md)）。

この構成では、Pythonの依存関係を**uvと`uv.lock`**で管理し、モデルを**`huggingface-hub`**で取得します。
OSの証明書ストアと追加CAを利用できるため、会社のLANやプロキシの設定にも対応できます。
Windowsでは、初回導入・モデルの追加・通常の起動にそれぞれ専用のbatを用意しています。

| やりたいこと | Windowsで使うファイル |
| --- | --- |
| 初めてセットアップする | **`START-HERE.bat`** |
| 初回に選ばなかったモデルを後から追加する | **`ADD-MODEL.bat`** |
| 導入済みモデルを起動する・起動時の設定を変更する | **`RUN-STRATA.bat`**、または`run-<model>.bat` |
| セットアップ時の設定を変更し、起動する | `SETUP.bat` |
| Strataを起動せずに更新する | `UPDATE.bat` |
| 自分のPCで速度を測定する | `BENCH.bat` |

<p align="center"><a href="https://github.com/Niko1221/Strata/releases/download/v0.1.10/Pagoda.mp4"><img src="docs/media/pagoda-preview.webp" width="720" alt="Strataのモデルが生成した、ブラウザーで動くボクセルの塔と庭園"></a><br>
<sub>RTX 5070、IQ3_S、128Kコンテキストで、1回の指示から作成した庭園 ·
<a href="https://github.com/Niko1221/Strata/releases/download/v0.1.10/Pagoda.mp4">動画全編（49秒）</a></sub></p>

<a id="what-you-need"></a>

## 必要な環境

下表は、主にQwen3.8-Flash-Nextの標準サイズを使う場合の目安です。モデルと設定によって必要量は変わります。

| 項目 | 目安 |
| --- | --- |
| **GPU** | NVIDIA GeForce RTX 20 / 30 / 40 / 50シリーズ、または対応するAMD Radeon。標準構成は**VRAM 12 GB以上**が目安 |
| **RAM** | **32 GB以上**。容量に合うモデルを選択。64 GBではQ2_0〜IQ3_Sを選べるが、大きいUnslothモデルはさらに必要 |
| **ディスク** | 標準モデル本体だけで約66〜84 GB。変換後のパックやMTPにも空き容量が必要。モデルを追加する場合は必要量が増える。SSDを推奨 |
| **OS** | Windows 10 / 11またはLinux。対応するGPUドライバーが必要 |
| **Python・依存関係** | uvが`.venv`を用意。対応するPythonがなければ取得。uv自体も見つからなければローカルに導入 |

対応するAMD GPUにはRX 7900 XT / XTX、RX 7800 XT / 7700 XT、RX 9060 XT、RX 9070 / 9070 XT、
Radeon AI PRO R9700、RX 6800 / 6900シリーズなどがあります。詳細は[AMDの対応状況](docs/AMD_HIP.md)を参照してください。
2枚以上のGPUでモデルを分担することもできます（[マルチGPU](docs/MULTI_GPU.md)）。

次の環境にも試験的な対応があります。対応状況と必要な手順は各ページを確認してください。

- [旧世代GPU](docs/OLDER_GPUS.md)：Tesla P40 / V100、GTX 10、Radeon VII / MI50、RX 6700 XT、RX 5500 XTなど
- [Intel Arc](docs/INTEL_ARC.md)：Linuxでソースからビルド
- [Appleシリコン搭載Mac](docs/MAC.md)：M1〜M5、macOS 15以降。Metalエンジンをビルド
- [AMD Ryzen AI Max（Strix Halo）](docs/STRIX_HALO.md)
- [AVX2非対応の旧世代CPU](docs/INSTALL.md#older-cpus-experimental)

必要な環境の詳細は[インストール手順](docs/INSTALL.md#what-you-need)を参照してください。

<a id="install"></a>
<a id="or-do-it-yourself"></a>

## 初回セットアップ

Strata-jtcのフォルダーを用意し、Windowsでは**`START-HERE.bat`をダブルクリック**します。
NVIDIA / AMDのGPUを検出して対応するエンジンを用意し、次の項目を選択します。

1. モデルの種類とサイズ
2. コンテキスト長：モデルが一度に扱えるテキストの量
3. Vision：画像の読み取りを使うかどうか

各項目でEnterを押すと、そのPCに対する推奨値または既存の設定が選ばれます。
モデルをダウンロードして準備し、起動が完了すると`http://127.0.0.1:8080`を開きます。
ダウンロードが中断した場合は再実行すると再開します。

ターミナルでモデルなどを指定することもできます。次の例は、ダウンロードと準備まで行い、起動は後で行います。

```powershell
.\START-HERE.bat --family qwen --model IQ2_XS --vision yes --no-start
```

`--yes`を追加すると質問せず推奨設定を使います。Visionも使いたい場合は`--vision yes`などを明示します。
モデルの容量と必要なディスク容量は選択した種類によって異なります。

> モデルの起動時には、大量のデータをRAMに読み込み、その一部をGPU用に固定するため、PCの動作が遅くなることがあります。
> 元のStrataの案内では1〜3分程度、初回はさらに長くかかる場合があります。ウィンドウの処理状況を確認して待ってください。

**Linux：** Strata-jtcのフォルダーで`./setup.sh`を実行します。
**Mac：** 最初に`xcode-select --install`でAppleのCommand Line Toolsを導入し、`./setup.sh`を実行します。
Mac用エンジンのビルド手順と対応状況は[Macの手順](docs/MAC.md)を参照してください。

<a id="let-your-ai-set-it-up"></a>

AIコーディングアシスタントにセットアップを依頼する場合は、このチェックアウトを指定して次のように伝えます。

```text
このPCにStrata-jtcをセットアップしてください。このリポジトリーのdocs/AI_SETUP.mdに従い、
GPU、RAM、ディスク容量を確認して、PCに合ったモデルを導入してください。
```

[MCPサーバー](docs/MCP_SERVER.md)を使った導入・起動・停止にも対応しています。

## 別のモデルを後から追加する

初回に選ばなかったモデルは、**`ADD-MODEL.bat`をダブルクリック**して追加します。
モデルの種類、サイズ、コンテキスト長、Visionを選ぶと、**ダウンロードと利用準備だけ**を行います。
完了後にモデルは起動しません。導入済みの共通ファイルは再利用します。
同じモデル・サイズを選んだ場合は、そのモデルの設定変更になります。

モデルを指定して追加する例：

```powershell
# 別の量子化サイズを追加
.\ADD-MODEL.bat --family qwen --model IQ3_S

# Swift 1.5を追加
.\ADD-MODEL.bat --family swift --model IQ2_XS

# Coderを推奨設定で、質問なしで追加
.\ADD-MODEL.bat --family coder --yes

# GLM-5.3-Flashを追加（量子化をメニューで選択）
.\ADD-MODEL.bat --family glm53
```

追加が終わったら、導入済みのモデルを確認して起動します。

```powershell
.\RUN-STRATA.bat --list-models
.\RUN-STRATA.bat --model swift-iq2_xs
```

`RUN-STRATA.bat`の`STRATA_MODEL`に設定ファイル名やモデル名を保存しておくこともできます。
セットアップが作成したモデル別の`run-<model>.bat`を使えば、そのモデルを直接起動できます。

Linux / Macでは`./setup.sh --setup --no-start`を実行します。
設定を変更してそのまま起動したい場合は、Windowsでは`SETUP.bat`、Linux / Macでは`./setup.sh --setup`を使います。

## GLM-5.3-Flashを追加する

`ADD-MODEL.bat`のモデル選択で**GLM-5.3-Flash**を選ぶか、`--family glm53`を指定します。
1 bitから8 bit、BF16まで12種類を選択でき、必要な分割ファイルをすべて取得します。
最小の`UD-IQ1_S`でも**約93.09 GB**です。作者のメモリーの目安は**RAMとVRAMの合計100 GB以上**です。
目安を下回る場合はSSDから読み込む設定にしますが、起動や速度は保証されません。

```powershell
# 最小の量子化を、コンテキスト2048・ポート8081で追加。取得後には起動しない
.\ADD-MODEL.bat --family glm53 --model UD-IQ1_S --context 2048 --port 8081 --yes

# 起動設定を確認してから起動
.\RUN-STRATA.bat --model glm53-ud-iq1_s --port 8081 --dry-run
.\RUN-STRATA.bat --model glm53-ud-iq1_s --port 8081
```

GLMではllama.cppのブラウザー画面とOpenAI互換APIを使います。この導入はテキスト専用です。
Qwenの速度の測定値やVision、MTP、エキスパートキャッシュの設定をGLMへ流用できません。
GPUへの割り当てとMoEのCPU計算もbatから変更できます。量子化別の容量、設定例、検証状況は
[GLMの手順](docs/GLM_SETUP.md)を参照してください。

`START-HERE.bat --calibrate`による速度の自動調整は、現在はStrata本体のQwen用エンジンが対象です。
GLMでは利用できません（[対応状況と調整候補](docs/GLM_SETUP.md#自動調整--calibrateの対応状況)）。

このPC（Ryzen 7 7700、RAM約32 GiB、RTX 5070 Ti）では、`UD-IQ1_S`を全量取得し、
コンテキスト1024でモデル読み込みとAPI生成を確認しました。読み込みは約20秒、短い生成の出力速度は
約1.57トークン/秒でした。測定条件と制約は[GLMの実測結果](docs/GLM_SETUP.md#このpcでの実測2026年10月15日)を参照してください。

## 通常の起動と設定変更

セットアップ後は**`RUN-STRATA.bat`をダブルクリック**します。先頭の設定欄で次の値を変更できます。

| 設定 | 指定する値 |
| --- | --- |
| `STRATA_MODEL` | `auto`で最近使ったモデル。`iq2_xs`、`swift-iq2_xs`、`strata-iq2_xs.json`など |
| `STRATA_VISION` | `keep`で保存済み設定、`on` / `off`でON / OFF、`gpu` / `cpu`で画像エンコーダーの実行先 |
| `STRATA_CONTEXT` | `auto`で保存済み設定。`32768`、`65536`、`262144`などトークン数 |
| `STRATA_PORT` | `auto`で保存済み設定。`8080`、`8081`など1〜65535のポート番号 |
| `STRATA_GPU` | `auto`で保存済みGPU選択。`0`、`1`、`0,1`など |
| `STRATA_BROWSER` | `auto`で保存済み設定。`yes`でブラウザーを開く、`no`で開かない |
| `STRATA_HOST` | 通常は`127.0.0.1`。ほかのアドレスを使う場合はAPIキーが必要 |

例えば、画像をOFFにして、コンテキスト65536、ポート8081で起動する設定は次のとおりです。

```bat
if not defined STRATA_VISION set "STRATA_VISION=off"
if not defined STRATA_CONTEXT set "STRATA_CONTEXT=65536"
if not defined STRATA_PORT set "STRATA_PORT=8081"
```

コマンドラインからも指定できます。`--dry-run`はモデルを読み込まず設定だけを表示します。

```powershell
.\RUN-STRATA.bat --model iq2_xs --vision off --context 65536 --port 8081 --dry-run
.\RUN-STRATA.bat --model iq2_xs --vision off --context 65536 --port 8081
```

この変更は今回の起動に適用し、保存済みのモデルJSON設定を書き換えません。
VisionをONにするには、そのモデルの画像エンコーダーを先に導入する必要があります。
未導入なら`SETUP.bat --vision yes`で対象モデルを選んでください。
コンテキストを大きく増やすと必要なメモリーも増えるため、RAM / VRAMやKVの設定も調整したい場合は`SETUP.bat`を使います。
詳しくは[起動設定の手順](docs/UV_SETUP.md#セットアップ後の起動)を参照してください。

停止するには起動したウィンドウを閉じます。`START-HERE.bat`から導入済みモデルを起動する方法も引き続き利用できます。

## 会社のLAN・プロキシ・SSL証明書

モデルと画像エンコーダーの取得には`huggingface-hub`を使います。
固定リビジョン、既存のSHA-256検証、`HF_ENDPOINT`によるミラー指定を維持し、ダウンロード済みのファイルを再利用します。
uvとPythonのダウンロード処理はOSの信頼済み証明書を利用します。会社のCAがOSに登録されていれば、そのCAも利用できます。
証明書検証とホスト名の検証は有効のままです。

プロキシや未登録の会社CAを指定する場合の例：

```powershell
$env:HTTPS_PROXY = "http://proxy.example:8080"
$env:HTTP_PROXY = $env:HTTPS_PROXY
$env:NO_PROXY = "localhost,127.0.0.1"
$env:SSL_CERT_FILE = "C:\certs\company-ca.pem"
.\START-HERE.bat
```

CA証明書は会社から提供されたPEM形式のファイルを指定します。必要なら同じ設定で`ADD-MODEL.bat`を実行できます。
会社側の接続先制限や認証がある場合は、その設定も必要です。
[batへの設定方法・ダウンロード再開・Xetの扱い](docs/UV_SETUP.md#会社のlanプロキシca証明書)も確認してください。

## uvによる依存関係の管理

Pythonの依存関係の正本は`pyproject.toml`と`uv.lock`です。`requirements.txt`は互換性のための生成物です。

```powershell
# ロックした依存関係を同期。他モデル用のGPUパッケージも残す
uv sync --locked --inexact

# 依存関係の追加・削除
uv add PACKAGE
uv remove PACKAGE

# uvからセットアップを実行
uv run --locked python setup.py
```

CUDAライブラリはセットアップが必要なバージョンを選びます。手動の場合は
`uv sync --locked --inexact --extra cuda13`または`--extra cuda12`を使います。
LinuxのROCmはGPUごとのAMD配布先を利用し、uvで導入します。
詳細と`requirements.txt`の再生成方法は[uvの手順](docs/UV_SETUP.md)を参照してください。

<a id="which-model-should-i-pick"></a>

## モデルの選び方

インストーラーはPCのRAMやGPUに合わせて候補を提示します。同じモデルでも量子化の種類により容量と品質が変わります。
下表は選択の目安です。OSやほかのアプリのための空きメモリーも必要です。

| RAM | 候補 | 補足 |
| --- | --- | --- |
| **32 GB** | Coder（IQ1_M） | コード向け。24 GBのGPUがある場合は低RAMモードでQ2_0 / IQ2_XSも選択可能 |
| **48 GB** | IQ2_XSまたはQ2_0 | 標準モデルの比較的小さいサイズ |
| **64 GB** | IQ3_S、IQ3_XXS、IQ2_XS | 現在のメニューは、必要な空きがある場合にIQ3_Sを推奨。速度を重視する場合は小さいサイズも選択可能 |
| **96 GB以上** | IQ3_S、Unsloth UD-IQ4_XS / UD-Q4_K_XL | 大きいモデルの候補。RAMが足りない分をSSDから読む構成では速度が下がる |
| **128〜192 GB** | Unsloth UD-Q5_K_XL / UD-Q6_K_XL / Q8_0 | 大きい量子化モデルをRAMに保持する構成向け |

追加メニューでは次の種類を選べます。利用できる種類はバックエンドによって異なります。

| `--family` | 種類 | 補足 |
| --- | --- | --- |
| `qwen` | Qwen3.8-Flash-Next | Q2_0、IQ2_XS、IQ3_XXS、IQ3_S |
| `swift` | Swift 1.5 | IQ2_XS、IQ3_XXS、IQ3_S。応答前の思考を短くする調整を加えたモデル |
| `coder` | Coder | コード用データに基づいてエキスパートを半分にしたモデル。サイズはIQ1_M |
| `unsloth` | Unslothの量子化モデル | UD-IQ4_XS、UD-Q4_K_XL、UD-Q5_K_XL、UD-Q6_K_XL、Q8_0。ダウンロードは約94〜188 GB |
| `nvfp4` | NVFP4形式のモデル | NVIDIA専用。AMD / Intel向けメニューでは表示しない |
| `qwen36` | Qwen3.6-35B-A3B | より小さい別モデル。CUDA / HIPで利用でき、Visionは未対応 |
| `glm53` | GLM-5.3-Flash | 専用llama.cppエンジン。12種類の量子化、最小約93 GB。テキスト専用 |

Coderはコード以外や日本語を含むCJK言語で弱くなる場合があります。一般用途では全エキスパートを保持する
Q2_0、IQ2_XS、IQ3_Sなども検討してください。モデル作者によるCoderのSWE-bench Verifiedの値は元モデルの91%です。
Unslothの大きいモデルは、RAMが不足するとSSDからエキスパートを読みながら回答するため、NVMe SSDが有用です。
[モデルの容量・測定値・対応状況](docs/MODELS.md)に詳細があります。
[OrcaRouterのUncensored IQ3_XXS](docs/MODELS.md#orcarouter-uncensored-iq3_xxs)はメニューに含めず、手動の導入手順を使います。

<a id="how-fast-is-it"></a>

## 速度の測定例

以下は元のStrataに掲載された測定値です。GPU、CPU、RAM、エンジンのバージョン、モデルやコンテキスト長で結果は変わります。
「回答生成」は出力速度、「入力処理」は32Kトークンの入力を読む速度です。トークンはモデルが扱うテキストの単位です。

**NVIDIA：RTX 5070（12 GB）、Ryzen 5 7600、RAM 64 GB**

| サイズ | 回答生成 | 入力処理 |
| --- | ---: | ---: |
| Q2_0 | 94トークン/秒 | 2,650トークン/秒 |
| IQ2_XS | 79トークン/秒 | 2,090トークン/秒 |
| IQ3_XXS | 62トークン/秒 | 1,750トークン/秒 |
| IQ3_S | 53トークン/秒 | 1,620トークン/秒 |
| Coder | 55トークン/秒 | 2,180トークン/秒 |

Q2_0はエンジン0.1.36、それ以外は0.1.26の測定です。4Kの回答生成と32Kの入力を使っています。

**AMD：RX 9070 XT（16 GB）、Ryzen 9 3900X、RAM 47 GB、Linux**

| サイズ | 回答生成 | 入力処理 |
| --- | ---: | ---: |
| Q2_0 | 60トークン/秒 | 1,160トークン/秒 |
| IQ2_XS | 52トークン/秒 | 1,110トークン/秒 |
| Coder | 44トークン/秒 | 1,420トークン/秒 |

長いコンテキストでの結果やほかのGPUの測定値は[速度の詳細](docs/DETAILS.md#speed-measured)と
[コミュニティーの測定結果](docs/COMMUNITY_BENCHMARKS.md)を参照してください。
`BENCH.bat`（Linuxでは`./bench.sh`）で、自分のPCのチャット・入力処理・エージェント利用を測定できます。
[測定と結果の共有方法](docs/COMMUNITY_BENCHMARKS.md#run-the-benchmark)も用意しています。

<a id="using-it"></a>

## アプリとの接続と使い方

<p align="center"><img src="docs/media/runpagoda.png" width="900" alt="StrataのMonitorタブと、庭園のコードを書いているコーディングエージェント"><br>
<sub>左はモデルとPCの状態を表示するMonitor、右は庭園を作成するコーディングエージェント</sub></p>

- **ブラウザー：** `http://127.0.0.1:8080`を開きます。Chatで会話し、MonitorでGPU / CPU / RAMの状態を確認できます。
- **OpenAI互換アプリ：** 接続先を`http://127.0.0.1:8080/v1`にします。APIキー未設定のローカル構成なら任意の値を使えます。キーを設定した構成では、そのキーを指定します。
- **Anthropic互換アプリ：** `http://127.0.0.1:8080/v1/messages`を利用できます。Claude Codeでは`ANTHROPIC_BASE_URL=http://127.0.0.1:8080`を指定します。
- **Responses APIを使うアプリ：** `/v1/responses`に対応します。[Codex CLIなどの接続手順](docs/DETAILS.md#the-responses-api-and-codex-cli)を参照してください。
- **思考の量：** チャットやアプリの設定でoff / low / medium / highを選べます。offは思考を省略します。
- **画像：** 対応する画像エンコーダーを導入し、VisionをONにして、チャットやアプリから画像を添付します。対応状況はGPUとバックエンドによって異なります。
- **同時リクエスト：** 既定では1件ずつ処理します。複数の同時処理はモデル設定の`"parallel": 2`などで有効にできます（[同時処理の説明](docs/BATCHING.md)）。追加のVRAMを使います。

別のPCやスマートフォンから利用する場合は、APIキーを設定してから公開先を変更します。

```powershell
$env:STRATA_API_KEY = "ここに十分長いAPIキーを設定"
.\RUN-STRATA.bat --host 0.0.0.0
```

ポートを変更した場合は、アプリ側のURLも同じ番号に変更してください。
詳しくは[チャットの保存先](docs/INSTALL.md#where-things-are-stored)と[APIの説明](docs/DETAILS.md#using-it)を参照してください。

<a id="optional-more-speed-on-one-card-when-the-whole-model-fits-in-ram"></a>

## 任意の速度調整

1枚のGPUを使い、全エキスパートがRAMに収まる構成では、次の設定を試せます。
設定ファイルは**Strata-jtcフォルダーの`strata-<model>.json`**です。

- **回答生成：** `"args"`に`"--adapt-async", "1"`を追加します。RTX 5070、Windows、Q2_0では生成速度が4〜5%、コードや長い文書で7〜10%向上した測定があります。既定の設定とは回答が少し変わる場合があります。
- **Windowsでの入力処理：** `"env"`に`"STRATA_PIN_BY_NEED": "1"`を追加します。RTX 5070では入力処理が4.4%向上した測定があります。

どちらもRubenTorneyによる任意の設定です（#1904、#1905）。JSONの既存の`args`や`env`に追加し、Strataを再起動します。
元に戻すには追加した項目を削除します。詳しい構成条件と保存先は[インストール手順](docs/INSTALL.md)を参照してください。

## 更新とファイルの保存先

Windowsの`UPDATE.bat`は、Gitで取得したコピーならコードを更新し、モデルを起動せずにエンジンや設定を確認します。
ローカルに変更したファイルがある場合、Gitの更新が止まることがあります。更新前に起動中のモデルを停止してください。
Linux / Macではコードを更新した後、`./setup.sh --update`で導入済みの環境を確認します。

| 内容 | 保存先 |
| --- | --- |
| Python環境・エンジン | Strata-jtcフォルダーの`.venv`、`engine`など |
| モデル・パック・MTP | 通常はStrata-jtcフォルダーの隣にある`Strata-data`。`--data-dir`で変更可能 |
| モデルの起動設定・ログ | Strata-jtcフォルダーの`strata-<model>.json`、`strata-<model>.log` |
| 起動用ファイル | `RUN-STRATA.bat`と、セットアップが作成する`run-<model>.bat` / `.sh` |
| チャット履歴 | ブラウザーのローカルストレージ。別のブラウザーやプライベートウィンドウとは共有しない |

<a id="something-went-wrong"></a>

## 困ったとき

- **ダウンロード・導入が途中で止まる：** 初回なら`START-HERE.bat`、追加導入なら同じ引数で`ADD-MODEL.bat`を再実行します。
- **SSL証明書のエラー：** OSに登録された会社CA、`SSL_CERT_FILE`、プロキシ設定を確認します。[証明書の手順](docs/UV_SETUP.md#会社のlanプロキシca証明書)を参照してください。
- **起動するモデルが見つからない：** `RUN-STRATA.bat --list-models`で確認し、未導入なら`ADD-MODEL.bat`で追加します。
- **VisionをONにできない：** 対象モデルの画像エンコーダーを導入済みか、バックエンドが対応するか確認します。
- **PCが極端に遅い・ディスクアクセスが続く：** RAMの空きを確認し、ほかのアプリを閉じるか、小さいモデルを選びます。
- **8080番ポートを使えない：** Strataやほかのサーバーが起動済みか確認します。`STRATA_PORT`または`--port`で別の番号に変更できます。

[トラブルシューティング](docs/TROUBLESHOOTING.md)にも対処方法があります。
問題を報告する場合は、認証情報を除いた`strata-<model>.log`を添えて[元のStrataのissue](https://github.com/Niko1221/Strata/issues)を確認してください。
セキュリティー上の問題は[SECURITY.md](SECURITY.md)の方法で非公開に報告します。

<a id="how-does-it-work"></a>

## 仕組み

Qwen3.8-Flash-Nextのような大きいモデルは、通常、大容量のGPUメモリーを使います。
Strataは頻繁に使うエキスパートをGPUに置き、残りの処理をCPUとシステムRAMで分担します。
RAMが足りない構成では、エキスパートの一部をSSDから必要に応じて読みます。

<p align="center"><img src="docs/media/how-it-works.svg" width="860" alt="頻繁に使うエキスパートをGPUに置き、RAMとSSDを組み合わせる構成"></p>

標準モデルには24,576個のエキスパートがあり、各トークンで使う一部を選択します。
さらにMTPによる先読みでは、候補のトークンを本体がまとめて検証します。
長い入力も分割してまとめて処理します。

<p align="center"><img src="docs/media/guess-and-check.svg" width="860" alt="先読みした候補を大きいモデルがまとめて検証し、正しいものを採用する処理"></p>

[仕組みの説明](docs/HOW_IT_WORKS.md)、[技術的な詳細と測定条件](docs/DETAILS.md#how-it-works)、
[論文](docs/paper/Strata-Paper.pdf)を参照してください。

<a id="credits-and-license"></a>

## クレジットとライセンス

元のモデルはQwenチームの[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)です。
[ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF)、UkisAI（Swift 1.5）、Unslothによる
量子化・調整済みモデルを利用します。Strataは[llama.cpp / ggml](https://github.com/ggml-org/llama.cpp)の一部を使っています。
[クレジットの一覧](docs/HOW_IT_WORKS.md#credits)も参照してください。

Strata本体は[MITライセンス](LICENSE)です。一部のコードと各モデルには別のライセンスがあります。
利用するモデルごとに[ライセンスの説明](docs/HOW_IT_WORKS.md#license)を確認してください。

<a id="support-strata"></a>

## 元のStrataの開発を支援する

元のStrataは無料のオープンソースプロジェクトです。開発を支援する場合は、作者のページを利用できます。

<p align="center"><a href="https://buymeacoffee.com/strataengine"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="元のStrataの作者にコーヒー代を支援" height="50"></a></p>
