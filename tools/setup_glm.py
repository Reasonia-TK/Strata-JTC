"""GLM-5.3-Flashを量子化別に取得し、専用llama.cppエンジンの起動設定を作る。"""
from __future__ import annotations

import os
import platform
import tarfile
import zipfile
from pathlib import Path

from glm_models import (
    CALIBRATION_UNSUPPORTED, CATALOG, FAMILY, MAX_CONTEXT, MEMORY_GB, QUANTS, TITLE, catalog_url, recommended_quant,
)

RELEASE = "b11617"
RELEASE_BASE = f"https://github.com/ggml-org/llama.cpp/releases/download/{RELEASE}/"
# 公式配布のGitHub asset digest。モデルと実行エンジンの版を両方固定する。
ASSETS = {
    "windows-cuda": [
        ("llama-b11617-bin-win-cuda-13.4-x64.zip", 153522270,
         "199352e34a774d698ae1735d80c64b84fa08047c33f74f14244dc4d72b58821e"),
        ("cudart-llama-bin-win-cuda-13.4-x64.zip", 423535356,
         "738f8c251ac22b70c3ae6f83a10cf222725df0395246a2cf58f32bdb85fbe668"),
    ],
    "windows-cpu": [("llama-b11617-bin-win-cpu-x64.zip", 19553620,
                     "1bad07f7993889a1f7431ad647904294f56919bf0bc84f4021327db1641a411c")],
    "windows-vulkan": [("llama-b11617-bin-win-vulkan-x64.zip", 32183619,
                        "540649b52663e8c9c94613288824dc4c96dfb7b226d2ec2507dfd1279dc4c60c")],
    "linux-cpu": [("llama-b11617-bin-ubuntu-x64.tar.gz", 17774259,
                   "bc9c8bd3488e5778137c2289d951af60a94077a6bea51b7e30461033b084e07f")],
}


def choose_backend(a):
    import setup
    backend = a.llama_backend
    if backend != "auto":
        return backend
    if setup.WIN:
        cards = setup.gpus()
        if any(setup.driver_major(g) >= 610 for g in cards):
            return "cuda"
        if cards or setup.amd_gpus():
            return "vulkan"
    return "cpu"


def extract_archive(archive, folder):
    """展開先を限定し、アーカイブ内のリンクと外向きのパスを拒否する。"""
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                if not (folder / member.filename).resolve().is_relative_to(folder) or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("実行エンジンのzipに安全でないパスが含まれています")
            z.extractall(folder)
    else:
        with tarfile.open(archive) as t:
            for member in t.getmembers():
                if not (folder / member.name).resolve().is_relative_to(folder) or not (member.isfile() or member.isdir()):
                    raise ValueError("実行エンジンのtarに安全でないパスが含まれています")
            t.extractall(folder, filter="data")


def install_runtime(a, backend):
    import setup
    if a.llama_server:
        exe = Path(a.llama_server).expanduser().resolve()
        if not exe.is_file():
            setup.fail(f"llama-serverがありません: {exe}")
        return exe
    system = "windows" if setup.WIN else "linux"
    key = f"{system}-{backend}"
    if platform.machine().lower() not in ("amd64", "x86_64") or key not in ASSETS:
        setup.fail(f"このOS/CPUの{backend}版は自動導入の対象外です",
                   "GLM対応版を用意し、--llama-server PATH で指定してください（Windows x64: CUDA/Vulkan/CPU、Linux x64: CPU）")
    folder = setup.ROOT / "engine" / "llama.cpp" / f"{RELEASE}-{backend}"
    name = "llama-server.exe" if setup.WIN else "llama-server"
    ready = folder / ".strata-ready"
    exes = list(folder.rglob(name)) if folder.exists() else []
    if ready.exists() and len(exes) == 1:
        return exes[0]
    for name, size, sha in ASSETS[key]:
        archive = setup.ROOT / "engine" / "llama.cpp" / "downloads" / name
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists() or archive.stat().st_size != size:
            setup.download(RELEASE_BASE + name, archive, "GLM実行エンジン: " + name)
        setup.verify_sha256(archive, size, sha)
        extract_archive(archive, folder)
    exes = list(folder.rglob("llama-server.exe" if setup.WIN else "llama-server"))
    if len(exes) != 1:
        setup.fail("配布物にllama-serverが1つだけ含まれていません")
    ready.write_text(RELEASE + "\n", encoding="utf-8")
    return exes[0]


def install(a):
    import setup
    if getattr(a, "calibrate", False):
        setup.fail(CALIBRATION_UNSUPPORTED)
    from serve.llama_runtime import gpu_layers_value
    layers = gpu_layers_value(a.gpu_layers)
    backend = choose_backend(a)
    ram = setup.ram_gb() * 2**30 / 1e9
    cards = setup.gpus() if backend == "cuda" else (setup.gpus() + setup.amd_gpus()) if backend == "vulkan" else []
    # 統合GPUの共有メモリをRAMに重ねて加算しない。
    vram = max((g.get("vram_gb", 0) * 2**30 / 1e9 for g in cards if not g.get("uma")), default=0)
    memory = ram + vram
    setup.say(f"\n{TITLE}\n  RAM: {ram:.1f} GB / 専用VRAM: {vram:.1f} GB / エンジン: {backend}")
    names = list(QUANTS)
    for i, q in enumerate(names, 1):
        setup.say(f"  {i:2}) {q:12} ダウンロード {QUANTS[q]['size'] / 1e9:.2f} GB "
                  f"({len(QUANTS[q]['files'])}分割)、RAM+VRAM目安 {MEMORY_GB[q]} GB")
    if a.check:
        fits = [q for q in names if memory >= MEMORY_GB[q]]
        setup.say("  容量の目安を満たす量子化: " + ", ".join(fits) if fits else
                  "  作者の最小目安100 GBを下回ります。SSDから読む構成は速度・起動とも未保証です。")
        return 0 if fits else 1
    if a.model and a.model not in QUANTS:
        setup.fail(f"GLMには{a.model}がありません", "量子化: " + ", ".join(names))
    rec = recommended_quant(memory)
    quant = a.model or names[int(setup.ask("量子化レベルを選択", [str(i) for i in range(1, len(names) + 1)],
                                         str(names.index(rec) + 1), a.yes)) - 1]
    low_memory = memory < MEMORY_GB[quant]
    if low_memory:
        # 明示的な --model は既存setupと同様、容量不足でも取得する選択を表す。
        setup.confirm_risk(f"{quant}のRAM+VRAM目安は{MEMORY_GB[quant]} GB、このPCは{memory:.1f} GBです。"
                           "SSDから読むため極端に遅くなるか、起動できない場合があります。", bool(a.model), a.yes,
                           "GLMのメモリ容量が作者の目安を下回ります", "量子化を明示する場合: --family glm53 --model UD-IQ1_S --yes",
                           "  ダウンロードを続けますか？")
    context = a.context if a.context is not None else int(setup.ask("コンテキスト長（トークン数）",
                                       ["1024", "2048", "4096", "8192", "16384", "32768", "65536", "131072"],
                                       "2048" if low_memory else "8192", a.yes))
    if not 1 <= context <= MAX_CONTEXT:
        setup.fail(f"GLMのコンテキスト長は1〜{MAX_CONTEXT}トークンです")
    port = a.port if a.port is not None else 8080
    if not 1 <= port <= 65535:
        setup.fail("ポート番号は1〜65535です")
    if a.host and a.host != "127.0.0.1" and not (a.api_key or os.environ.get("STRATA_API_KEY")):
        setup.fail("127.0.0.1以外での起動にはAPIキーが必要です")
    if a.vision not in (None, "no", "none"):
        setup.fail("このGLMの導入はテキスト専用です", "--vision no を指定してください")
    if a.source == "modelscope":
        setup.fail("GLMの取得はHugging Faceを利用します", "--source huggingface を指定してください")
    tag = FAMILY + "-" + quant.lower()
    folder = Path(a.gguf_dir).expanduser().resolve() if a.gguf_dir else Path(a.models_dir).expanduser().resolve() / tag
    files = []
    for item in QUANTS[quant]["files"]:
        path = folder / item["path"]
        if a.gguf_dir and not path.exists():
            path = folder / Path(item["path"]).name
        files.append(path)
    need = sum(item["size"] for item, path in zip(QUANTS[quant]["files"], files)
               if not path.is_file() or path.stat().st_size != item["size"])
    if need and a.gguf_dir:
        setup.fail("指定フォルダーにはGLMの全分割ファイルが揃っていません", "--gguf-dirを外すとダウンロードできます")
    if need and setup.free_gb(folder) < need / 1e9 + 2:
        setup.fail(f"空き容量が不足しています: {folder}（モデルの残り約{need / 1e9:.1f} GB + エンジン等2 GB）")
    setup.sync_dependencies()
    exe = install_runtime(a, backend)
    for item, path in zip(QUANTS[quant]["files"], files):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size != item["size"]:
            setup.download(catalog_url(item, setup.hf_endpoint()), path)
        setup.verify_sha256(path, item["size"], item["sha256"])
    cpu_moe = a.cpu_moe == "on" or (a.cpu_moe == "auto" and QUANTS[quant]["size"] / 1e9 > vram)
    args = ["--model", str(files[0]), "--alias", "glm-5.3-flash-" + quant.lower(), "--ctx-size", str(context),
            "--parallel", "1", "--gpu-layers", "0" if backend == "cpu" else layers,
            "--load-mode", "mmap", "--jinja", "--temp", "1.0", "--top-p", "0.95"]
    if cpu_moe:
        args.append("--cpu-moe")
    if low_memory:
        args += ["--no-warmup", "--no-repack", "--batch-size", "128", "--ubatch-size", "64"]
    cfg = {"runtime": "llama.cpp", "arch": "glm5-next", "exe": str(exe), "args": args,
           "cwd": str(exe.parent), "model_name": "glm-5.3-flash-" + quant.lower(), "family": FAMILY,
           "quant": quant, "model_files": list(map(str, files)), "model_revision": CATALOG["revision"],
           "runtime_version": RELEASE if not a.llama_server else "custom", "backend": backend,
           "low_memory": low_memory, "port": port, "open_browser": a.browser is not False}
    if a.host:
        cfg["host"] = a.host
    if a.api_key:
        cfg["api_key"] = a.api_key
    if a.gpu is not None or a.gpus:
        if a.gpus != "all":
            cfg["gpu"] = a.gpus or a.gpu
    path = setup.ROOT / f"strata-{tag}.json"
    setup.write_setup_config(path, cfg)
    script = setup.write_run_script(tag, path, port, cfg["open_browser"])
    setup.say(f"\n準備が完了しました。次回は {script.name} または RUN-STRATA.bat --model {tag} で起動できます。")
    setup.say(f"  ブラウザー: http://127.0.0.1:{port} / OpenAI API: http://127.0.0.1:{port}/v1")
    return 0 if a.no_start else setup.start(path, port, open_browser=cfg["open_browser"])
