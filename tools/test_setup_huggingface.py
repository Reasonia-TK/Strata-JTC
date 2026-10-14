"""Hub downloads, old partial files and verified corporate TLS, without the internet."""
from __future__ import annotations

import contextlib
import io
import os
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup
import strata_network
import httpx
from huggingface_hub._local_folder import get_local_download_paths


class HubDownload(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="strata hub ")
        self.addCleanup(self.temp.cleanup)
        self.dst = Path(self.temp.name) / "renamed.gguf"
        self.url = setup.hf("ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF") + "Q2_0/model.gguf"
        for patch in (mock.patch("strata_network.configure_network"),
                      mock.patch.dict(os.environ, {"STRATA_SOURCE": "huggingface"}),
                      mock.patch.object(setup.time, "sleep")):
            patch.start()
            self.addCleanup(patch.stop)

    def completed(self, **kw):
        path = Path(kw["local_dir"]) / kw["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"complete model")
        return str(path)

    def test_pinned_subfolder_uses_hub_and_moves_to_requested_filename(self):
        with mock.patch("huggingface_hub.hf_hub_download", side_effect=self.completed) as hub:
            setup.download(self.url, self.dst)
            setup.download(self.url, self.dst)
        hub.assert_called_once()
        kw = hub.call_args.kwargs
        self.assertEqual(kw["revision"], setup.HF_REVISIONS[kw["repo_id"]])
        self.assertEqual(kw["filename"], "Q2_0/model.gguf")
        self.assertEqual(self.dst.read_bytes(), b"complete model")
        self.assertTrue(setup.done(self.dst))
        self.assertFalse((Path(kw["local_dir"]) / kw["filename"]).exists())

    def test_explicit_mirror_is_passed_to_hub(self):
        url = self.url.replace("https://huggingface.co", "https://company-hf.example")
        with mock.patch("huggingface_hub.hf_hub_download", side_effect=self.completed) as hub:
            setup.download(url, self.dst)
        self.assertEqual(hub.call_args.kwargs["endpoint"], "https://company-hf.example")

    def test_old_complete_part_is_finalized_without_body_download(self):
        self.dst.with_name(self.dst.name + ".part").write_bytes(b"complete model")
        meta = SimpleNamespace(size=14, etag="etag")
        with mock.patch("huggingface_hub.get_hf_file_metadata", return_value=meta), \
                mock.patch("huggingface_hub.hf_hub_download") as hub:
            setup.download(self.url, self.dst)
        hub.assert_not_called()
        self.assertEqual(self.dst.read_bytes(), b"complete model")
        self.assertTrue(setup.done(self.dst))

    def test_old_partial_is_adopted_and_resume_survives_a_retry(self):
        self.dst.with_name(self.dst.name + ".part").write_bytes(b"complete ")
        calls = 0

        def resume(**kw):
            nonlocal calls
            paths = get_local_download_paths(Path(kw["local_dir"]), kw["filename"])
            part = paths.incomplete_path("etag")
            self.assertEqual(part.read_bytes(), b"complete ")
            calls += 1
            if calls == 1:
                raise httpx.ReadError("interrupted")
            paths.file_path.write_bytes(part.read_bytes() + b"model")
            part.unlink()
            return str(paths.file_path)

        with mock.patch("huggingface_hub.get_hf_file_metadata", return_value=SimpleNamespace(size=14, etag="etag")), \
                mock.patch("huggingface_hub.hf_hub_download", side_effect=resume):
            setup.download(self.url, self.dst)
        self.assertEqual(calls, 2)
        self.assertEqual(self.dst.read_bytes(), b"complete model")

    def test_real_hub_downloader_resumes_with_http_range(self):
        """モックしたHub関数ではなく、固定版のHTTP転送が中断位置を引き継ぐ。"""
        self.dst.with_name(self.dst.name + ".part").write_bytes(b"complete ")
        ranges = []
        body = b"complete model"

        def respond(request):
            headers = {"X-Repo-Commit": "a" * 40, "ETag": '"etag"', "Content-Length": str(len(body))}
            if request.method == "HEAD":
                return httpx.Response(200, headers=headers)
            ranges.append(request.headers.get("range"))
            start = int(request.headers["range"].removeprefix("bytes=").removesuffix("-"))
            headers.update({"Content-Length": str(len(body) - start),
                            "Content-Range": f"bytes {start}-{len(body)-1}/{len(body)}"})
            return httpx.Response(206, headers=headers, content=body[start:])

        with httpx.Client(transport=httpx.MockTransport(respond)) as client, \
                mock.patch("huggingface_hub.utils._http.get_session", return_value=client):
            setup.download(self.url, self.dst)
        self.assertEqual(ranges, ["bytes=9-"])
        self.assertEqual(self.dst.read_bytes(), body)
        self.assertTrue(setup.done(self.dst))

    def test_failure_never_marks_a_download_complete_or_logs_credentials(self):
        output = io.StringIO()
        with mock.patch("huggingface_hub.hf_hub_download",
                        side_effect=httpx.ConnectError("https://user:secret@example.com?token=private")), \
                contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            setup.download(self.url, self.dst)
        self.assertFalse(setup.done(self.dst))
        self.assertNotIn("secret", output.getvalue())
        self.assertNotIn("private", output.getvalue())
        self.assertIn("SSL_CERT_FILE", output.getvalue())

    def test_closed_client_after_connection_failure_is_recreated(self):
        calls = [RuntimeError("Cannot send a request, as the client has been closed."), None]
        def download(**kw):
            first = calls.pop(0)
            if first is not None:
                raise first
            return self.completed(**kw)
        with mock.patch("huggingface_hub.hf_hub_download", side_effect=download), \
                contextlib.redirect_stdout(io.StringIO()):
            setup.download(self.url, self.dst)
        self.assertEqual(self.dst.read_bytes(), b"complete model")
        self.assertEqual(strata_network.configure_network.call_count, 2)

    def test_offline_error_does_not_switch_to_an_unpinned_revision(self):
        from huggingface_hub.errors import LocalEntryNotFoundError
        with mock.patch("huggingface_hub.hf_hub_download", side_effect=LocalEntryNotFoundError("offline")) as hub, \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            setup.download(self.url, self.dst)
        self.assertEqual(hub.call_count, 5)
        self.assertTrue(all(call.kwargs["revision"] != "main" for call in hub.call_args_list))


class CorporateTLS(unittest.TestCase):
    def test_verification_and_hostname_checks_stay_enabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            ctx = strata_network.tls_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_custom_ca_and_cert_directory_are_added(self):
        context = mock.Mock()
        with mock.patch.dict(os.environ, {"SSL_CERT_FILE": "company.pem", "SSL_CERT_DIR": "company-certs"}, clear=True), \
                mock.patch("truststore.SSLContext", return_value=context):
            strata_network.tls_context()
        context.load_verify_locations.assert_any_call(cafile="company.pem", capath="company-certs")

    def test_requests_ca_bundle_is_supported(self):
        context = mock.Mock()
        with mock.patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": "company.pem"}, clear=True), \
                mock.patch("truststore.SSLContext", return_value=context):
            strata_network.tls_context()
        context.load_verify_locations.assert_any_call(cafile="company.pem", capath=None)


if __name__ == "__main__":
    unittest.main()
