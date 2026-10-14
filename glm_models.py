"""GLM-5.3-Flashの固定GGUF一覧。StrataのQwen用エンジンとは別に扱う。"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parent / "data" / "glm53-flash.json").read_text(encoding="utf-8"))
FAMILY = "glm53"
TITLE = "GLM-5.3-Flash (Unsloth GGUF / llama.cpp)"
QUANTS = CATALOG["models"]
MAX_CONTEXT = 1048576

# 作者の公開範囲を参考にした判定用の目安（RAM + VRAM、GB）。
# IQ1_Mと5/6 bitはファイル容量 + 約8〜10 GBからの概算。
MEMORY_GB = dict(zip(QUANTS, [100, 105, 115, 115, 128, 150, 162, 210, 251, 302, 350, 650]))


def is_external(cfg):
    return cfg.get("runtime") == "llama.cpp"


def recommended_quant(memory_gb):
    fits = [q for q in QUANTS if memory_gb >= MEMORY_GB[q]]
    return fits[-1] if fits else next(iter(QUANTS))


def catalog_url(item, endpoint="https://huggingface.co"):
    return f"{endpoint.rstrip('/')}/{CATALOG['repo']}/resolve/{CATALOG['revision']}/{item['path']}"
