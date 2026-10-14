"""Start an installed Strata model using settings from RUN-STRATA.bat."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup  # noqa: E402
from glm_models import is_external  # noqa: E402
from serve import llama_runtime  # noqa: E402
from serve.launch_options import apply_overrides  # noqa: E402


def auto_integer(value):
    if value.lower() == "auto":
        return None
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use auto or a positive integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("use auto or a positive integer")
    return number


def select_config(model, configs):
    if model.lower() == "auto":
        if configs:
            return configs[0]
        raise ValueError("導入済みモデルがありません。初回は START-HERE.bat、追加導入は ADD-MODEL.bat を実行してください")
    candidate = Path(model).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if candidate.is_file() and setup.model_config(candidate):
        return candidate.resolve()
    for cfg in configs:
        if model.lower() in (cfg.name.lower(), cfg.stem.lower(), cfg.stem.removeprefix("strata-").lower()):
            return cfg
    raise ValueError(f"モデル設定が見つかりません: {model}。未導入モデルは ADD-MODEL.bat で追加できます。"
                     "導入済みモデルの一覧は RUN-STRATA.bat --list-models で確認してください")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="auto", help="auto, installed model tag, or path to a strata-*.json config")
    ap.add_argument("--context", type=auto_integer, default=None, help="auto or a positive token count")
    ap.add_argument("--vision", type=str.lower, choices=["keep", "on", "off", "gpu", "cpu"], default="keep")
    ap.add_argument("--port", type=auto_integer, default=None, help="auto or a port from 1 to 65535")
    ap.add_argument("--gpu", default="auto", help="auto, one GPU number, or numbers separated by commas")
    ap.add_argument("--browser", choices=["auto", "yes", "no"], default="auto")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--gpu-layers", default="auto", help="GLM専用: autoで保存値、all、またはGPUレイヤー数")
    ap.add_argument("--cpu-moe", choices=["auto", "on", "off"], default="auto", help="GLM専用: MoEのCPU計算")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="show effective settings without loading a model")
    a = ap.parse_args(argv)
    configs = setup.installed_configs()
    if a.list_models:
        for cfg in configs:
            print(cfg.name)
        if not configs:
            print("導入済みモデルがありません。初回は START-HERE.bat を実行してください。")
        print("別のモデルを追加する場合は ADD-MODEL.bat を実行してください。")
        return 0
    try:
        path = select_config(a.model, configs)
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
        if is_external(cfg):
            effective = llama_runtime.apply_overrides(cfg, a.context, a.vision, a.gpu_layers, a.cpu_moe)
        else:
            if a.gpu_layers != "auto" or a.cpu_moe != "auto":
                raise ValueError("--gpu-layersと--cpu-moeはGLM専用です")
            effective = apply_overrides(cfg, a.context, a.vision)
        port = a.port if a.port is not None else int(cfg.get("port", 8080))
        if not 1 <= port <= 65535:
            raise ValueError("port must be from 1 to 65535")
        if a.host != "127.0.0.1" and not (os.environ.get("STRATA_API_KEY") or cfg.get("api_key")):
            raise ValueError("set STRATA_API_KEY before using a host other than 127.0.0.1")
        if a.gpu.lower() != "auto" and not all(n.strip().isdigit() for n in a.gpu.split(",")):
            raise ValueError("gpu must be auto, a GPU number, or numbers separated by commas")
    except (OSError, ValueError) as e:
        ap.error(str(e))
    effective["host"] = a.host
    if a.gpu.lower() != "auto":
        effective["gpu"] = a.gpu
    print(f"Config: {path.name}", flush=True)
    print(setup.settings_summary(effective, port), flush=True)
    encoder = effective.get("vision")
    print("Vision: " + ("on (GPU)" if encoder.get("gpu") else "on (CPU)") if encoder else "Vision: off", flush=True)
    if is_external(cfg):
        print("実行エンジン: llama.cpp（GLM用）", flush=True)
        if a.dry_run:
            llama_runtime.command(effective, port, a.host, effective.get("gpu"))
            return 0
        path.touch()
        return llama_runtime.start(effective, port=port, host=a.host,
                                   open_browser=a.browser == "yes" or (a.browser == "auto" and cfg.get("open_browser") is not False))
    if a.dry_run:
        return 0
    cmd = [sys.executable, str(ROOT / "serve" / "server.py"), "--engine", "strata", "--config", str(path),
           "--port", str(port), "--host", a.host, "--vision", a.vision]
    if a.context is not None:
        cmd += ["--context", str(a.context)]
    if a.gpu.lower() != "auto":
        cmd += ["--gpu", a.gpu]
    if a.browser == "yes" or (a.browser == "auto" and cfg.get("open_browser") is not False):
        cmd.append("--open")
    # Update recency without changing any saved setting.
    path.touch()
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
