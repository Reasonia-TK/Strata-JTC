"""Runtime launch settings, config preservation and Windows batch argument forwarding."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serve.launch_options import apply_overrides
from tools import launch_strata as launch
import setup


def config():
    return {"exe": "strata.exe", "args": ["--native", "model.gguf", "--max-context", "32768"],
            "vision": {"exe": "strata-vision.exe", "gpu": True}, "port": 8080}


class Overrides(unittest.TestCase):
    def test_off_then_on_preserves_original_vision_and_args(self):
        saved = config()
        text = json.dumps(saved)
        off = apply_overrides(saved, 65536, "off")
        self.assertNotIn("vision", off)
        self.assertIn("65536", off["args"])
        on = apply_overrides(saved, vision="on")
        self.assertTrue(on["vision"]["gpu"])
        self.assertEqual(json.dumps(saved), text)

    def test_long_context_adds_rope_scaling_with_the_derived_factor(self):
        effective = apply_overrides(config(), 524288)
        self.assertEqual(setup.flag_value(effective["args"], "--rope-scaling"), "yarn")
        self.assertEqual(setup.flag_value(effective["args"], "--rope-scale"), "2")

    def test_resizing_an_extended_context_recomputes_its_factor(self):
        cfg = config()
        cfg["args"] += ["--rope-scaling", "linear", "--rope-scale", "2"]
        effective = apply_overrides(cfg, 786432)
        self.assertEqual(setup.flag_value(effective["args"], "--rope-scaling"), "linear")
        self.assertEqual(setup.flag_value(effective["args"], "--rope-scale"), "3")

    def test_invalid_context_or_missing_encoder_fails_before_start(self):
        with self.assertRaises(ValueError):
            apply_overrides(config(), 0)
        cfg = config()
        cfg.pop("vision")
        with self.assertRaisesRegex(ValueError, "not installed"):
            apply_overrides(cfg, vision="on")

    def test_cpu_encoder_is_used_without_changing_saved_gpu_setting(self):
        cfg = config()
        effective = apply_overrides(cfg, vision="cpu")
        self.assertFalse(effective["vision"]["gpu"])
        self.assertGreaterEqual(effective["vision"]["threads"], 1)
        self.assertTrue(cfg["vision"]["gpu"])


class Launcher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="strata 起動 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "strata-q2_0.json"
        self.path.write_text(json.dumps(config()), encoding="utf-8")
        for patch in (mock.patch.object(launch, "ROOT", self.root), mock.patch.object(setup, "ROOT", self.root)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_model_selection_accepts_tag_path_and_auto(self):
        for model in ("auto", "q2_0", "strata-q2_0.json", str(self.path)):
            with self.subTest(model=model):
                self.assertEqual(launch.select_config(model, [self.path]), self.path)

    def test_uninstalled_model_points_to_the_add_model_entry(self):
        with self.assertRaisesRegex(ValueError, "ADD-MODEL.bat"):
            launch.select_config("swift-iq2_xs", [self.path])

    def test_list_models_includes_the_add_model_entry(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(launch.main(["--list-models"]), 0)
        self.assertIn(self.path.name, output.getvalue())
        self.assertIn("ADD-MODEL.bat", output.getvalue())

    def test_launch_passes_all_settings_without_rewriting_config(self):
        before = self.path.read_bytes()
        with mock.patch.object(launch.subprocess, "call", return_value=7) as call, \
                contextlib.redirect_stdout(io.StringIO()):
            result = launch.main(["--model", "q2_0", "--vision", "off", "--context", "65536", "--port", "8081",
                                  "--gpu", "0,1", "--browser", "no"])
        self.assertEqual(result, 7)
        args = call.call_args.args[0]
        self.assertEqual(args[args.index("--port") + 1], "8081")
        self.assertEqual(args[args.index("--context") + 1], "65536")
        self.assertEqual(args[args.index("--vision") + 1], "off")
        self.assertEqual(args[args.index("--gpu") + 1], "0,1")
        self.assertNotIn("--open", args)
        self.assertEqual(self.path.read_bytes(), before)

    def test_dry_run_never_starts_or_changes_recency(self):
        before = self.path.stat().st_mtime_ns
        with mock.patch.object(launch.subprocess, "call") as call, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch.main(["--dry-run", "--context", "65536"]), 0)
        call.assert_not_called()
        self.assertEqual(self.path.stat().st_mtime_ns, before)

    def test_remote_host_requires_a_key_and_invalid_port_fails(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(launch.subprocess, "call") as call, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launch.main(["--host", "0.0.0.0"])
            with self.assertRaises(SystemExit):
                launch.main(["--port", "65536"])
        call.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows batch execution")
    def test_windows_runner_dry_run_reaches_the_launcher(self):
        with mock.patch.dict(os.environ, {"UV_CACHE_DIR": str(ROOT / ".uv-cache")}):
            result = subprocess.run(["cmd", "/d", "/c", str(ROOT / "RUN-STRATA.bat"),
                                     "--model", str(self.path), "--vision", "off", "--context", "65536",
                                     "--port", "8081", "--gpu", "auto", "--browser", "no", "--dry-run"],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--max-context 65536", result.stdout)
        self.assertIn("127.0.0.1:8081", result.stdout)
        self.assertIn("Vision: off", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows batch execution")
    def test_generated_batch_forwards_values_and_preserves_exit_code(self):
        # Execute the generated bat with a harmless fake RUN-STRATA, including a path with spaces.
        (self.root / "RUN-STRATA.bat").write_bytes(
            b'@echo off\r\necho model=%STRATA_MODEL%\r\necho port=%STRATA_PORT%\r\n'
            b'echo browser=%STRATA_BROWSER%\r\necho forwarded=%*\r\nexit /b 7\r\n')
        with mock.patch.object(setup, "WIN", True):
            script = setup.write_run_script("Q2_0", self.path, 8081, False)
        result = subprocess.run(["cmd", "/d", "/c", str(script), "--dry-run"], capture_output=True,
                                text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertIn("port=8081", result.stdout)
        self.assertIn("browser=no", result.stdout)
        self.assertIn("forwarded=--dry-run", result.stdout)


if __name__ == "__main__":
    unittest.main()
