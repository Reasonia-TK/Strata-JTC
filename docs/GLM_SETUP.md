# GLM-5.3-Flashの追加と起動

Strata-jtcでは、[UnslothのGLM-5.3-Flash GGUF](https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF)を
量子化レベルごとにダウンロードし、**GLM対応版のllama.cpp**で起動します。
Strata本体のQwen用エンジンとはモデル構造が異なるため、GLM用の実行ファイルを別に用意します。
Qwenの導入済みモデルと併用でき、`RUN-STRATA.bat`で起動するモデルを選べます。

## 量子化と容量

次の容量は、固定リビジョン`a38483c8cd5df544f53d70fb281afe97369d5ab6`の全分割ファイルの合計です。
GBは10億バイトです。実行エンジン、OS、コンテキスト用のメモリーは別途必要です。

| 量子化 | モデルのダウンロード容量 | 分割数 |
| --- | ---: | ---: |
| `UD-IQ1_S` | 93.09 GB | 3 |
| `UD-IQ1_M` | 97.58 GB | 3 |
| `UD-IQ2_XXS` | 101.84 GB | 4 |
| `UD-Q2_K_XL` | 108.72 GB | 4 |
| `UD-IQ3_XXS` | 120.37 GB | 4 |
| `UD-Q3_K_XL` | 147.54 GB | 4 |
| `UD-IQ4_XS` | 156.82 GB | 5 |
| `UD-Q4_K_XL` | 199.71 GB | 6 |
| `UD-Q5_K_XL` | 240.31 GB | 6 |
| `UD-Q6_K_XL` | 291.83 GB | 7 |
| `Q8_0` | 340.98 GB | 8 |
| `BF16` | 641.64 GB | 14 |

[作者の案内](https://unsloth.ai/docs/models/glm-5.3-flash)では、RAMと専用VRAMの合計の目安は
1 bitで100 GB、2 bitで115 GB、3 bitで128〜150 GB、4 bitで162〜210 GBです。
共有メモリーを使う統合GPUでは、同じメモリーをRAMとVRAMへ重ねて加算しません。
量子化を大きくすると一般に元の重みに近づきますが、このPCでの品質や速度を比較した値ではありません。

容量が目安を下回る場合、セットアップは確認を表示します。量子化を明示した`--model ... --yes`は、
容量不足でも取得する指定になります。この場合はmmap、短いコンテキスト、事前の空実行を省略する設定を使います。
SSDからの読み込みが増えるため、極端に遅くなることや、起動できないことがあります。

## ダウンロード

Windowsでは`ADD-MODEL.bat`のモデル選択でGLMを選ぶか、次のコマンドを使います。

```powershell
# 量子化をメニューで選ぶ
.\ADD-MODEL.bat --family glm53

# 量子化と起動設定を指定する。完了後に自動起動しない
.\ADD-MODEL.bat --family glm53 --model UD-IQ1_S --context 2048 --port 8081 --yes

# 別の量子化を後から追加する
.\ADD-MODEL.bat --family glm53 --model UD-IQ3_XXS --port 8082 --yes

# PCの容量と量子化一覧を表示する。モデルは取得しない
.\START-HERE.bat --family glm53 --check
```

保存先を変える場合は`--models-dir D:\AI\models`を追加します。
取得済みファイルは再利用し、中断した取得は同じコマンドで再開します。
`huggingface-hub`で固定リビジョンを取得し、**全分割ファイルの容量とSHA-256**を検証します。
先頭ファイルが小さくても、残りの大容量ファイルがなければ起動できません。
ミラー、会社のプロキシ、追加CAは[uvと証明書の手順](UV_SETUP.md#会社のlanプロキシca証明書)を使います。

手元のGGUFを利用する場合は`--gguf-dir D:\AI\GLM\UD-IQ1_S`を指定します。
選んだ量子化の**すべての分割ファイル**が必要です。違うリビジョンの分割ファイルを混ぜないでください。

Linuxでは`./setup.sh --setup --no-start --family glm53 --model UD-IQ1_S --yes`を使います。
自動導入の対象はWindows x64のCUDA / Vulkan / CPU版とLinux x64のCPU版です。
LinuxでGPUを使う場合など、別ビルドを使うときはGLM対応版の`llama-server`を用意して
`--llama-server /path/to/llama-server --llama-backend cuda`を指定します。
macOS用のGLM自動導入はこのメニューの対象外です。

## 起動と設定変更

セットアップが作った`run-glm53-ud-iq1_s.bat`をダブルクリックするか、次のように実行します。

```powershell
.\RUN-STRATA.bat --list-models
.\RUN-STRATA.bat --model glm53-ud-iq1_s --context 2048 --port 8081 --dry-run
.\RUN-STRATA.bat --model glm53-ud-iq1_s --context 2048 --port 8081
```

batの設定欄では次の値を変更できます。`auto`は保存済み設定を使います。

| 設定 | 用途 |
| --- | --- |
| `STRATA_MODEL` | 例: `glm53-ud-iq1_s`、`glm53-ud-iq3_xxs` |
| `STRATA_CONTEXT` | コンテキスト長。例: `1024`、`2048`、`8192`。増やすと必要なメモリーも増える |
| `STRATA_PORT` | 起動するポート。例: `8081`、`8082` |
| `STRATA_GPU` | GPU番号。例: `0`、`1`、`0,1` |
| `STRATA_GPU_LAYERS` | GPUに置くレイヤー数。`all`、`0`〜`46`など。`0`はCPUで計算 |
| `STRATA_CPU_MOE` | `on`でMoEの重みをCPUで計算、`off`でGPUへの配置も許可 |
| `STRATA_BROWSER` | `yes`で準備完了後にブラウザーを開く、`no`で開かない |
| `STRATA_VISION` | このGLM導入では`keep`または`off`。テキスト専用 |

セットアップ時のGPUレイヤー数の`auto`はllama.cppが空きVRAMに合わせて決めます。
起動batの`auto`はその設定を引き継ぎます。モデルがVRAMに収まらない場合、セットアップ時の
`--cpu-moe auto`はMoEのCPU計算を有効にします。

```powershell
# CPUでの起動を試す（CUDA版を導入済みでも使用可能）
.\RUN-STRATA.bat --model glm53-ud-iq1_s --gpu-layers 0 --cpu-moe on --context 1024 --port 8081

# GPU配置をllama.cppに任せ、MoEのCPU固定を外す
.\RUN-STRATA.bat --model glm53-ud-iq1_s --cpu-moe off --port 8081
```

表示される画面はllama.cppのチャット画面です。APIの接続先は`http://127.0.0.1:8081/v1`です。
APIのモデル名には`glm-5.3-flash-ud-iq1_s`など、導入時に表示された名前を使います。
この導入ではVisionやStrataのQwen用MTP・エキスパートキャッシュの設定は使いません。
通常は`127.0.0.1`で起動し、他のアドレスを指定する場合は`STRATA_API_KEY`が必要です。

## 自動調整（--calibrate）の対応状況

`START-HERE.bat --calibrate`はStrata本体のQwen用エンジンを実測して調整する機能です。
PCIe経由の処理配分、MTPの採用条件、CPUの処理スレッド数、エキスパートキャッシュを比較します。
**llama.cppで動かすGLMは対象外**です。GLMを指定した場合や、GLMだけを導入した状態で
`--calibrate`を実行した場合は、理由を表示して終了します。

GLMのGPUレイヤー数の自動決定は、空きメモリーに合わせるための処理です。
複数の設定で速度を測って最速の値を保存する処理ではありません。
GLMでもCPUのスレッド数、GPUへの配置、MoEのCPU計算、入力処理のバッチサイズは調整候補になりますが、
このリポジトリーにGLM用の速度自動調整はまだ実装していません。

比較測定には[llama.cpp公式のllama-bench](https://github.com/ggml-org/llama.cpp/blob/b11617/tools/llama-bench/README.md)
を利用できます。同じ量子化、コンテキスト、入力と出力の長さで、入力処理と生成の速度、メモリー使用量を
複数回測って判断します。このPCでGLMの調整前後を比較した結果はまだありません。

## 実行エンジンと検証

自動導入では、現在の`glm5-next` GGUF形式に対応する
[公式llama.cpp b11617](https://github.com/ggml-org/llama.cpp/releases/tag/b11617)を使います。
配布アーカイブも容量とGitHubが公開するSHA-256で確認し、`engine/llama.cpp/`へ展開します。
Windowsの自動選択はNVIDIAドライバー610以上でCUDA 13.4版、その他のGPUではVulkan版、GPUがなければCPU版です。
GPUドライバー自体は変更しません。

`huggingface-hub`は中断ファイルへの追記とHTTP Rangeによる再開を確認した1.15.0に固定しています。
このPCの実ダウンロードで、23,026,728,960バイトの中断位置から再開できました。
依存関係の版を変える場合は、再開テストを行ってから`uv.lock`を更新してください。

量子化別のファイル一覧、追加導入、既存Qwen設定の保持、起動時の上書き、全分割ファイルの存在確認は
`uv run python tools/test_setup_glm.py`で確認できます。
CUDA版の実行ファイルがRTX 5070 Tiを認識することも確認済みです。

### このPCでの実測（2026年10月15日）

`UD-IQ1_S`の全3ファイル、合計93,087,245,088バイトを実際に取得し、各SHA-256を検証しました。
`RUN-STRATA.bat`を通して起動し、モデル読み込み、モデル一覧API、チャット生成を確認しました。

| 項目 | 条件・結果 |
| --- | --- |
| CPU | AMD Ryzen 7 7700、8コア / 16スレッド |
| OS | Windows 11 Home、ビルド26200 |
| RAM | 31.29 GiB（約32 GiBのPC） |
| GPU | NVIDIA GeForce RTX 5070 Ti、VRAM 16,303 MiB、ドライバー610.88 |
| エンジン | 公式llama.cpp b11617、CUDA 13.4版 |
| 起動設定 | コンテキスト1024、並列数1、GPUレイヤーauto、MoEはCPU、mmap、事前の空実行なし |
| 接続先 | `http://127.0.0.1:8083`（8081番は別サービスが使用中） |
| 読み込みから準備完了 | 19.71秒（ヘルスチェックによる測定） |
| `GET /health` / `GET /v1/models` | 両方HTTP 200 |
| `POST /v1/chat/completions` | HTTP 200、入力19トークン・出力8トークン、全体25.03秒 |
| 入力処理・生成速度 | エンジンのtimingsでは約0.93・約1.57トークン/秒 |
| 空きRAM | 生成開始約20秒時点で1.24 GiBまで減少 |

8トークンの上限を指定した短い生成テストです。長文、長いコンテキスト、他の量子化、Vision、
別OS・GPUでの推論は確認していません。このPCの容量は作者の目安を下回るため、RAMの余裕が少ない構成です。
テスト後は今回のGLMプロセスを終了し、モデルと起動設定を残しています。
