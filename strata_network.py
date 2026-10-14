"""TLS settings shared by setup and its checkpoint downloader."""
from __future__ import annotations

import os
import ssl
import urllib.request


def tls_context():
    import certifi
    import truststore

    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Keep public roots as well as the OS store (including an installed company CA).
    context.load_verify_locations(certifi.where())
    cafile = (os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
              or os.environ.get("CURL_CA_BUNDLE"))
    capath = os.environ.get("SSL_CERT_DIR")
    if cafile or capath:
        context.load_verify_locations(cafile=cafile or None, capath=capath or None)
    return context


def configure_network():
    """Use the same verified TLS context for urllib and Hugging Face's HTTP client."""
    # Xet has its own Rust TLS client. The HTTP download path uses the context below
    # and works with HTTPS_PROXY and custom company CAs. Set 0 explicitly to use Xet.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
    import httpx
    from huggingface_hub import set_client_factory
    from huggingface_hub.utils._http import hf_request_event_hook

    context = tls_context()
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)))
    set_client_factory(lambda: httpx.Client(verify=context, follow_redirects=True, timeout=60, trust_env=True,
                                           event_hooks={"request": [hf_request_event_hook]}))


def network_hint():
    return ("check HTTPS_PROXY / HTTP_PROXY and the OS trusted certificates; for a company CA bundle, "
            "set SSL_CERT_FILE to its PEM file (docs/UV_SETUP.md)")
