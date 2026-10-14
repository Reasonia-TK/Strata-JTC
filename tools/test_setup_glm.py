"""GLMの追加導入、分割ファイル、起動オプション、既存Qwen設定の保護を確認する。"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup
from glm_models import CATALOG, QUANTS
from serve import llama_runtime
from tools import launch_strata, setup_glm


def config():
    return {"runtime": "llama.cpp", "arch": "glm5-next", "exe": "llama-server.exe",
            "args": ["--model", "first.gguf", "--ctx-size", "2048", "--gpu-layers", "auto", "--cpu-moe"],
            "backend": "cuda", "port": 8090, "family": "glm53", "quant": "UD-IQ1_S"}


def options(**values):
    args = dict(llama_backend="cpu", llama_server=None, gpu_layers="auto", cpu_moe="auto", check=False,
                model="UD-IQ1_S", yes=True, context=1024, port=8090, host=None, api_key=None, vision="no",
                source=None, gguf_dir=None, models_dir=None, browser=False, gpu=None, gpus=None, no_start=True)
    return argparse.Namespace(**(args | values))


class Startup(unittest.TestCase):
    def test_uses_llama_context_and_keeps_saved_settings(self):
        original = config()
        snapshot = json.dumps(original)
        effective = llama_runtime.apply_overrides(original, context=4096, vision="off", gpu_layers="0", cpu_moe="off")
        self.assertEqual(setup.flag_value(effective["args"], "--ctx-size"), "4096")
        self.assertEqual(setup.flag_value(effective["args"], "--gpu-layers"), "0")
        self.assertNotIn("--max-context", effective["args"])
        self.assertNotIn("--rope-scaling", effective["args"])
        self.assertNotIn("--cpu-moe", effective["args"])
        self.assertEqual(json.dumps(original), snapshot)

    def test_invalid_context_vision_and_gpu_layers_fail_before_loading(self):
        for opts in ({"context": 0}, {"context": 1048577}, {"vision": "on"}, {"gpu_layers": "-1"}):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                llama_runtime.apply_overrides(config(), **opts)

    def test_saved_device_and_network_overrides_reach_llama_server(self):
        cfg = config() | {"gpu": "0,1"}
        cmd, _ = llama_runtime.command(cfg, port=8081)
        self.assertEqual(setup.flag_value(cmd, "--device"), "CUDA0,CUDA1")
        self.assertEqual(setup.flag_value(cmd, "--port"), "8081")
        self.assertEqual(setup.flag_value(cmd, "--host"), "127.0.0.1")

    def test_api_key_is_in_environment_and_absent_from_command(self):
        cfg = config() | {"api_key": "test-secret"}
        with mock.patch.dict(os.environ, {"STRATA_API_KEY": "test-env-secret"}):
            cmd, env = llama_runtime.command(cfg, host="0.0.0.0")
        self.assertEqual(env["LLAMA_API_KEY"], "test-env-secret")
        self.assertNotIn("test-secret", " ".join(cmd))
        self.assertNotIn("test-env-secret", " ".join(cmd))

    def test_network_access_without_key_is_refused(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            llama_runtime.command(config(), host="0.0.0.0")

    def test_cpu_engine_cannot_silently_ignore_gpu_choice(self):
        with self.assertRaises(ValueError):
            llama_runtime.command(config() | {"backend": "cpu"}, gpu=1)

    def test_missing_second_shard_stops_before_process_start(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first.gguf"
            first.touch()
            cfg = config() | {"exe": str(first), "model_files": [str(first), str(first.with_name("second.gguf"))]}
            with mock.patch.object(llama_runtime.subprocess, "Popen") as popen, self.assertRaisesRegex(ValueError, "second.gguf"):
                llama_runtime.start(cfg, open_browser=False)
            popen.assert_not_called()

    def test_common_launcher_dispatches_to_external_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "strata-glm53-ud-iq1_s.json"
            path.write_text(json.dumps(config()), encoding="utf-8")
            with mock.patch.object(setup, "installed_configs", return_value=[path]), \
                 mock.patch.object(llama_runtime, "start", return_value=7) as start, \
                 mock.patch.object(launch_strata.subprocess, "call") as native, contextlib.redirect_stdout(io.StringIO()):
                code = launch_strata.main(["--model", str(path), "--context", "4096", "--gpu-layers", "0", "--browser", "no"])
            self.assertEqual(code, 7)
            self.assertEqual(setup.flag_value(start.call_args.args[0]["args"], "--ctx-size"), "4096")
            native.assert_not_called()
            self.assertEqual(json.loads(path.read_text()), config())

    def test_setup_start_bypasses_qwen_engine_upgrade_and_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "strata-glm53-ud-iq1_s.json"
            path.write_text(json.dumps(config()), encoding="utf-8")
            with mock.patch.object(llama_runtime, "start", return_value=0) as start, \
                 mock.patch.object(setup, "ensure_engine_for") as native, mock.patch.object(setup, "refresh_draft_vocab") as draft:
                self.assertEqual(setup.start(path, 8081), 0)
            start.assert_called_once()
            native.assert_not_called()
            draft.assert_not_called()
            self.assertEqual(setup.choices_from_config(path)["family"], "glm53")
            self.assertEqual(setup.calibration_targets([path], None, None), [])


class Installer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bytes = [b"first metadata shard", b"second weights shard", b"third weights shard"]
        self.items = [{"path": f"UD-IQ1_S/GLM-test-{i+1:05}-of-00003.gguf", "size": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                      for i, b in enumerate(self.bytes)]
        self.quants = {"UD-IQ1_S": {"size": sum(map(len, self.bytes)), "files": self.items}}
        self.exe = self.root / "llama-server.exe"
        self.exe.touch()
        for patch in (mock.patch.object(setup, "ROOT", self.root),
                      mock.patch.object(setup_glm, "QUANTS", self.quants),
                      mock.patch.object(setup, "ram_gb", return_value=32),
                      mock.patch.object(setup, "sync_dependencies"),
                      mock.patch.object(setup_glm, "install_runtime", return_value=self.exe)):
            patch.start()
            self.addCleanup(patch.stop)
        self.args = options(models_dir=str(self.root / "models"))

    def download(self, url, path, *args):
        item = next(i for i in self.items if url.endswith(i["path"]))
        path.write_bytes(self.bytes[self.items.index(item)])

    def test_installs_every_shard_and_keeps_existing_qwen_config(self):
        saved = self.root / "strata-q2_0.json"
        saved.write_bytes(b'{"exe":"qwen-engine","args":[],"port":8080}')
        snapshot = saved.read_bytes()
        with mock.patch.object(setup, "download", side_effect=self.download) as download, \
             mock.patch.object(setup, "start") as start, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup_glm.install(self.args), 0)
        self.assertEqual(download.call_count, 3)
        start.assert_not_called()
        self.assertEqual(saved.read_bytes(), snapshot)
        path = self.root / "strata-glm53-ud-iq1_s.json"
        cfg = json.loads(path.read_text())
        self.assertEqual(len(cfg["model_files"]), 3)
        self.assertEqual(cfg["runtime"], "llama.cpp")
        self.assertIn("--no-warmup", cfg["args"])
        self.assertEqual(setup.flag_value(cfg["args"], "--gpu-layers"), "0")
        self.assertTrue((self.root / "run-glm53-ud-iq1_s.bat").exists())
        with mock.patch.object(setup, "download") as again, contextlib.redirect_stdout(io.StringIO()):
            setup_glm.install(self.args)
        again.assert_not_called()

    def test_missing_shard_in_user_folder_prevents_network_download(self):
        self.args.gguf_dir = str(self.root)
        with mock.patch.object(setup, "download") as download, contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit):
            setup_glm.install(self.args)
        download.assert_not_called()

    def test_bad_gpu_layers_are_rejected_before_download(self):
        self.args.gpu_layers = "-1"
        with mock.patch.object(setup, "download") as download, self.assertRaises(ValueError):
            setup_glm.install(self.args)
        download.assert_not_called()

    def test_zero_context_and_port_are_refused_before_download(self):
        for field in ("context", "port"):
            with self.subTest(field=field), mock.patch.object(setup, "download") as download, \
                 contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                setup_glm.install(options(models_dir=self.args.models_dir, **{field: 0}))
            download.assert_not_called()

    def test_check_does_not_install_or_download(self):
        with mock.patch.object(setup, "download") as download, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup_glm.install(options(check=True)), 1)
        download.assert_not_called()
        setup.sync_dependencies.assert_not_called()
        setup_glm.install_runtime.assert_not_called()

    def test_cli_glm_choice_bypasses_qwen_checks_and_data_migration(self):
        with mock.patch.object(sys, "argv", ["setup.py", "--family", "glm53", "--model", "UD-IQ1_S", "--check"]), \
             mock.patch.object(setup_glm, "install", return_value=1) as install, \
             mock.patch.object(setup, "data_folder", side_effect=AssertionError("model files moved")), \
             mock.patch.object(setup, "gpus", side_effect=AssertionError("native GPU check")), \
             mock.patch.object(setup, "load_settings", return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(), 1)
        self.assertEqual(install.call_args.args[0].model, "UD-IQ1_S")

    def test_interactive_add_menu_routes_glm_to_its_own_installer(self):
        from tools.test_setup_golden import PROFILES, install as simulate_install
        ram, cards = PROFILES["64GB-1x32GB"]
        number = str(len(setup.menu_families(False)) + len(setup.OWN_PATH_FAMILIES) + 1)
        with mock.patch.object(setup_glm, "install", return_value=0) as install:
            code, out, _, _ = simulate_install(ram, cards, ["--setup", "--no-start"],
                                               answers={"Which model?": number})
        self.assertEqual(code, 0, out)
        install.assert_called_once()
        self.assertIn("GLM-5.3-Flash", out)

    def test_model_hash_mismatch_does_not_write_launch_config(self):
        def corrupt(url, path, *args):
            self.download(url, path, *args)
            path.write_bytes(b"x" * path.stat().st_size)
        with mock.patch.object(setup, "download", side_effect=corrupt), contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(SystemExit):
            setup_glm.install(self.args)
        self.assertFalse((self.root / "strata-glm53-ud-iq1_s.json").exists())


class ArchiveAndCatalog(unittest.TestCase):
    def test_quant_catalog_contains_complete_distinct_pinned_shard_sets(self):
        self.assertEqual(len(CATALOG["revision"]), 40)
        for quant, model in QUANTS.items():
            with self.subTest(quant=quant):
                self.assertEqual(model["size"], sum(i["size"] for i in model["files"]))
                count = len(model["files"])
                for number, item in enumerate(model["files"], 1):
                    self.assertTrue(item["path"].startswith(quant + "/"))
                    self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
                    self.assertTrue(item["path"].endswith(f"-{number:05}-of-{count:05}.gguf"))

    def test_zip_path_traversal_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "engine.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../outside.exe", b"bad")
            with self.assertRaises(ValueError):
                setup_glm.extract_archive(archive, Path(temp) / "output")
            self.assertFalse((Path(temp) / "outside.exe").exists())

    def test_tar_links_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "engine.tar.gz"
            with tarfile.open(archive, "w:gz") as t:
                item = tarfile.TarInfo("link")
                item.type, item.linkname = tarfile.SYMTYPE, "../outside"
                t.addfile(item)
            with self.assertRaises(ValueError):
                setup_glm.extract_archive(archive, Path(temp) / "output")


if __name__ == "__main__":
    unittest.main()
