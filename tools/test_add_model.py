"""Additional-model setup keeps existing settings and prepares the model without starting it."""
from __future__ import annotations

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
import setup
from tools.test_setup_golden import PROFILES, install


class AdditionalModel(unittest.TestCase):
    def add_model(self, argv, answers=None):
        existing = {"exe": "existing-strata", "args": ["--max-context", "32768"], "port": 8081,
                    "model_name": "my Qwen Q2_0", "sampling": {"temperature": 0.4}}
        snapshot = json.dumps(existing).encode("utf-8")
        written = []
        original_write = setup.write_setup_config

        def capture(path, cfg, source=None):
            saved = setup.ROOT / "strata-q2_0.json"
            self.assertEqual(saved.read_bytes(), snapshot)
            original_write(path, cfg, source)
            self.assertEqual(saved.read_bytes(), snapshot)
            written.extend(p.name for p in setup.installed_configs())

        start = mock.Mock(side_effect=AssertionError("a model was started during additional setup"))
        ram, gpus = PROFILES["64GB-1x32GB"]
        result = install(ram, gpus, ["--setup", "--no-start", *argv], answers=answers,
                         configs=[("strata-q2_0.json", existing)],
                         extra=[mock.patch.object(setup, "start", start),
                                mock.patch.object(setup, "write_setup_config", capture)])
        start.assert_not_called()
        return result, written

    def test_adds_a_different_size_without_replacing_the_first_model(self):
        (code, out, cfg, _), names = self.add_model(["--family", "qwen", "--model", "IQ2_XS"])
        self.assertEqual(code, 0, out)
        self.assertEqual(set(names), {"strata-q2_0.json", "strata-iq2_xs.json"})
        self.assertIn("iq2_xs", cfg["model_name"])

    def test_interactive_menu_can_add_another_family(self):
        (code, out, cfg, questions), names = self.add_model([], answers={"Which model?": "2", "Which size?": "1"})
        self.assertEqual(code, 0, out)
        self.assertTrue(any("Which model?" in q for q in questions))
        self.assertEqual(set(names), {"strata-q2_0.json", "strata-swift-iq2_xs.json"})
        self.assertIn("swift", cfg["model_name"])

    def test_adds_sc117_swift_without_replacing_qwen_settings(self):
        (code, out, cfg, _), names = self.add_model(["--family", "swift-abliterated", "--model", "IQ2_XS"])
        self.assertEqual(code, 0, out)
        self.assertEqual(set(names), {"strata-q2_0.json", "strata-swift-abliterated-iq2_xs.json"})
        self.assertEqual(cfg["model_name"], "swift-1.5-abliterated-iq2_xs")

    @unittest.skipUnless(os.name == "nt", "Windows batch execution")
    def test_batch_dispatches_install_only_and_preserves_exit_code(self):
        with tempfile.TemporaryDirectory(prefix="Strata 追加 ") as folder:
            path = Path(folder)
            batch = path / "ADD-MODEL.bat"
            batch.write_bytes((ROOT / "ADD-MODEL.bat").read_bytes())
            starter = path / "START-HERE.bat"
            for code in (0, 7):
                with self.subTest(code=code):
                    starter.write_bytes(f'@echo off\r\necho forwarded=%*\r\nexit /b {code}\r\n'.encode("utf-8"))
                    result = subprocess.run(["cmd", "/d", "/c", str(batch), "--family", "swift", "--model", "IQ2_XS"],
                                            capture_output=True, text=True, encoding="utf-8", timeout=10)
                    self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                    self.assertIn("forwarded=--setup --no-start --family swift --model IQ2_XS", result.stdout)
                    if code:
                        self.assertNotIn("処理が終了しました", result.stdout)


if __name__ == "__main__":
    unittest.main()
