"""導入済みのGLMをllama-serverで起動する。秘密値をコマンド表示に含めない。"""
from __future__ import annotations

import copy
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from glm_models import MAX_CONTEXT
from serve.launch_options import set_argument


def gpu_layers_value(value):
    value = str(value).lower()
    if value in ("auto", "all") or value.isdigit():
        return value
    raise ValueError("GPUへの割り当ては auto、all、または0以上のレイヤー数を指定してください")


def apply_overrides(cfg, context=None, vision="keep", gpu_layers="auto", cpu_moe="auto"):
    cfg = copy.deepcopy(cfg)
    if vision not in ("keep", "off"):
        raise ValueError("このGLMの起動設定はテキスト専用です。Visionは keep または off を指定してください")
    if context is not None:
        if not 1 <= context <= MAX_CONTEXT:
            raise ValueError(f"GLMのコンテキスト長は1〜{MAX_CONTEXT}トークンを指定してください")
        cfg["args"] = set_argument(cfg["args"], "--ctx-size", context)
    if gpu_layers != "auto":
        cfg["args"] = set_argument(cfg["args"], "--gpu-layers", gpu_layers_value(gpu_layers))
    if cpu_moe not in ("auto", "on", "off"):
        raise ValueError("CPUでのMoE計算は auto、on、off を指定してください")
    if cpu_moe != "auto":
        cfg["args"] = [x for x in cfg["args"] if x != "--cpu-moe"]
        if cpu_moe == "on":
            cfg["args"].append("--cpu-moe")
    cfg.pop("vision", None)
    return cfg


def command(cfg, port=None, host=None, gpu=None):
    args = list(cfg["args"])
    host = host or cfg.get("host", "127.0.0.1")
    port = int(port if port is not None else cfg.get("port", 8080))
    if not 1 <= port <= 65535:
        raise ValueError("ポート番号は1〜65535を指定してください")
    key = os.environ.get("STRATA_API_KEY") or cfg.get("api_key")
    if host != "127.0.0.1" and not key:
        raise ValueError("127.0.0.1以外での起動にはSTRATA_API_KEYが必要です")
    args = set_argument(args, "--host", host)
    args = set_argument(args, "--port", port)
    if gpu is None:
        gpu = cfg.get("gpu")
    if gpu is not None:
        gpu = ",".join(map(str, gpu)) if isinstance(gpu, list) else str(gpu)
        if not all(x.strip().isdigit() for x in gpu.split(",")):
            raise ValueError("GPUは0、1、0,1のように指定してください")
        if cfg.get("backend") not in ("cuda", "vulkan"):
            raise ValueError("GPUを指定するにはCUDAまたはVulkan版のGLMエンジンを導入してください")
        prefix = "CUDA" if cfg.get("backend") == "cuda" else "Vulkan"
        args = set_argument(args, "--device", ",".join(prefix + x.strip() for x in gpu.split(",")))
    env = dict(os.environ)
    # llama.cppの引数や子プロセスのログに秘密値を埋め込まない。
    if key:
        env["LLAMA_API_KEY"] = key
    return [cfg["exe"], *map(str, args)], env


def _open_when_ready(process, port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    url = f"http://127.0.0.1:{port}"
    for _ in range(1800):
        if process.poll() is not None:
            return
        try:
            with opener.open(url + "/health", timeout=1) as response:
                if response.status == 200:
                    if process.poll() is None:
                        webbrowser.open(url)
                    return
        except OSError:
            pass
        time.sleep(1)


def start(cfg, port=None, host=None, gpu=None, open_browser=True):
    cmd, env = command(cfg, port, host, gpu)
    missing = [p for p in [cfg["exe"], *cfg.get("model_files", [])] if not Path(p).is_file()]
    if missing:
        raise ValueError(f"必要なファイルがありません: {missing[0]}。ADD-MODEL.bat --family glm53 で修復してください")
    if cfg.get("low_memory"):
        print("メモリ容量が作者の目安を下回ります。SSDからの読み込みが多くなり、応答に長時間かかる場合があります。",
              flush=True)
    print(f"GLMをllama.cppで起動します: http://127.0.0.1:{port or cfg.get('port', 8080)}", flush=True)
    process = subprocess.Popen(cmd, cwd=cfg.get("cwd") or Path(cfg["exe"]).parent, env=env)
    if open_browser:
        threading.Thread(target=_open_when_ready, args=(process, port or cfg.get("port", 8080)), daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130
