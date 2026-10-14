"""Optional settings for one server start; saved model configs are left intact."""
from __future__ import annotations

import copy


def set_argument(args, name, value):
    """Replace every occurrence so an older duplicate cannot override this start."""
    result = []
    i = 0
    while i < len(args):
        if args[i] == name:
            if i + 1 >= len(args) or str(args[i + 1]).startswith("--"):
                raise ValueError(f"{name} has no value in the model config")
            i += 2
        else:
            result.append(args[i])
            i += 1
    if value is not None:
        result += [name, str(value)]
    return result


def apply_overrides(cfg, context=None, vision="keep"):
    if vision not in ("keep", "off", "on", "gpu", "cpu"):
        raise ValueError("vision must be keep, on, off, gpu, or cpu")
    cfg = copy.deepcopy(cfg)
    if context is not None:
        if context < 1:
            raise ValueError("context must be a positive token count")
        if not isinstance(cfg.get("args"), list):
            raise ValueError("context needs a Strata model config with engine args")
        import setup
        if setup.own_path_config(cfg):
            if context > 262144:
                raise ValueError("this model's engine has no RoPE extension; use context <= 262144")
            cfg["args"] = set_argument(cfg["args"], "--max-context", context)
        else:
            scaling = setup.flag_value(cfg["args"], "--rope-scaling")
            scaling, factor = setup.resolve_rope(context, scaling, None)
            cfg["args"] = set_argument(cfg["args"], "--max-context", context)
            cfg["args"] = set_argument(cfg["args"], "--rope-scaling", scaling)
            cfg["args"] = set_argument(cfg["args"], "--rope-scale", f"{factor:g}" if factor is not None else None)
    if vision == "off":
        cfg.pop("vision", None)
    elif vision in ("on", "gpu", "cpu"):
        if not cfg.get("vision"):
            raise ValueError("vision encoder is not installed for this model; run START-HERE.bat --setup --vision yes "
                             "and select this model first")
        if vision != "on":
            cfg["vision"]["gpu"] = vision == "gpu"
            if vision == "cpu":
                import os
                cfg["vision"].setdefault("threads", max(1, (os.cpu_count() or 8) // 2))
    return cfg
