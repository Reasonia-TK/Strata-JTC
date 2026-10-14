"""SC117版Swiftの量子化別URL、既存設定の保持、ネイティブパックと起動設定を確認する。"""
from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup
from tools.test_setup_golden import PROFILES, install

FAMILY = "swift-abliterated"
CATALOG = setup.SWIFT_ABLITERATED


class SwiftHeader:
    def __init__(self, path):
        # 通常のQwenとは異なり、SwiftのPLEテーブルは先頭の分割ファイルにある。
        names = ["per_layer_token_embd.weight"] if "00001-of" in str(path) else []
        self.tensors = [types.SimpleNamespace(name=n) for n in names]


class SwiftAbliterated(unittest.TestCase):
    def install_model(self, quant=None, vision="no", answers=None):
        ram, cards = PROFILES["64GB-1x32GB"]
        seen = []
        old = {"exe": "old-engine", "args": ["--max-context", "32768"], "port": 8080}
        configs = [("strata-iq2_xs.json", old | {"model_name": "original Qwen"}),
                   ("strata-swift-iq2_xs.json", old | {"model_name": "original Swift"}),
                   ("strata-glm53-ud-iq1_s.json", old | {"runtime": "llama.cpp", "family": "glm53", "quant": "UD-IQ1_S"})]

        def download(url, dst, *args):
            snapshots = {setup.ROOT / name: json.dumps(cfg).encode() for name, cfg in configs}
            for path, snapshot in snapshots.items():
                self.assertEqual(path.read_bytes(), snapshot)
            # Qwenの同名エンコーダーがあっても、SC117のコピーと混ぜない。
            original_encoder = dst.parent.parent / setup.FAMILIES["qwen"]["mmproj"]
            if not original_encoder.exists():
                original_encoder.parent.mkdir(parents=True, exist_ok=True)
                original_encoder.write_bytes(b"original Qwen vision encoder")
            self.assertEqual(original_encoder.read_bytes(), b"original Qwen vision encoder")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(b"")
            setup.mark(dst)
            seen.append((url, dst))

        args = ["--setup", "--no-start", "--context", "32768", "--vision", vision]
        if quant is not None:
            args += ["--family", FAMILY, "--model", quant]
        run, verify, start = mock.Mock(), mock.Mock(), mock.Mock(side_effect=AssertionError("model started"))
        result = install(ram, cards, args, answers=answers, avx512=True, configs=configs, extra=[
            mock.patch.object(setup, "download", side_effect=download),
            mock.patch.object(setup, "run", run), mock.patch.object(setup, "verify_sha256", verify),
            mock.patch.object(setup, "start", start),
            mock.patch.dict(sys.modules, {"gguf_reader": types.SimpleNamespace(GGUFFile=SwiftHeader)}),
        ])
        start.assert_not_called()
        return result, seen, run, verify

    def test_all_four_quants_fetch_the_pinned_pair_and_use_their_own_pack(self):
        for quant, data in CATALOG["models"].items():
            with self.subTest(quant=quant):
                (code, out, cfg, _), seen, run, verify = self.install_model(quant)
                self.assertEqual(code, 0, out)
                base = f"https://huggingface.co/{CATALOG['repo']}/resolve/{CATALOG['revision']}/"
                self.assertEqual([url for url, _ in seen], [base + f["path"] for f in data["files"]])
                self.assertEqual([call.args[1:] for call in verify.call_args_list],
                                 [(f["size"], f["sha256"]) for f in data["files"]])
                args = cfg["args"]
                first = setup.flag_value(args, "--native")
                self.assertTrue(first.endswith(Path(data["files"][0]["path"]).name))
                self.assertEqual(setup.flag_value(args, "--ple-gguf"), first)
                self.assertIn(f"/packs/swift-abliterated-{quant.lower()}", setup.flag_value(args, "--pack"))
                self.assertEqual(cfg["model_name"], f"swift-1.5-abliterated-{quant.lower()}")
                self.assertIn("--mtp", args)
                self.assertGreaterEqual(int(setup.flag_value(args, "--spec")), 2)
                scripts = [Path(c.args[0][1]).name for c in run.call_args_list]
                self.assertIn("iq_pack.py", scripts)
                self.assertNotIn("strata_pack.py", scripts)  # QwenのAVX-512用変換をSC117へ流用しない。

    def test_interactive_add_menu_lists_the_model_and_all_quants(self):
        number = str(setup.menu_families(False).index(FAMILY) + 1)
        (code, out, cfg, _), _, _, _ = self.install_model(
            answers={"Which model?": number, "Which size?": "2"})
        self.assertEqual(code, 0, out)
        self.assertIn("Swift 1.5 Abliterated", out)
        for q in CATALOG["models"]:
            self.assertIn(q, out)
        self.assertEqual(cfg["model_name"], "swift-1.5-abliterated-iq2_xs")

    def test_vision_encoder_has_its_own_folder_and_hash(self):
        (code, out, cfg, _), seen, _, verify = self.install_model("IQ2_XS", vision="cpu")
        self.assertEqual(code, 0, out)
        url, target = seen[-1]
        self.assertTrue(url.endswith("/" + CATALOG["mmproj"]["path"]))
        self.assertEqual(target.parent.name, FAMILY)
        self.assertIn("/models/swift-abliterated/", cfg["vision"]["mmproj"])
        self.assertEqual(verify.call_args.args[1:], (CATALOG["mmproj"]["size"], CATALOG["mmproj"]["sha256"]))

    def test_family_and_calibration_selection_do_not_confuse_it_with_swift(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = []
            for tag in ("swift-iq2_xs", "swift-abliterated-iq2_xs"):
                path = Path(temp) / f"strata-{tag}.json"
                path.write_text(json.dumps({"exe": "engine", "args": ["--max-context", "32768"]}), encoding="utf-8")
                paths.append(path)
            self.assertEqual(setup.choices_from_config(paths[0])["family"], "swift")
            self.assertEqual(setup.choices_from_config(paths[1])["family"], FAMILY)
            self.assertEqual(setup.choices_from_config(paths[1])["model"], "IQ2_XS")
            self.assertEqual(setup.calibration_targets(paths, "IQ2_XS", FAMILY), [paths[1]])
            self.assertEqual(setup.calibration_targets(paths, "IQ2_XS", "swift"), [paths[0]])

    def test_file_identification_and_existing_quant_choices(self):
        self.assertEqual(setup.family_models(FAMILY), ["Q2_0", "IQ2_XS", "IQ3_XXS", "IQ3_S"])
        self.assertEqual(setup.family_models("swift"), ["IQ2_XS", "IQ3_XXS", "IQ3_S"])
        for q, data in CATALOG["models"].items():
            self.assertEqual(setup.gguf_choice(Path(data["files"][0]["path"]).name), (FAMILY, q))
            self.assertEqual(setup.model_download_gb(setup.FAMILIES[FAMILY], q), data["size"] / 1e9)


if __name__ == "__main__":
    unittest.main()
