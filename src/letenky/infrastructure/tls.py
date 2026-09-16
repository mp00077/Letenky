"""Verified HTTPS with portable CA roots, including on packaged macOS apps."""
import ssl

import certifi


def create_tls_context() -> ssl.SSLContext:
    # Retain the roots configured for this Python installation and add Mozilla's
    # bundle. A frozen application must not rely on a build-machine CA path.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    context.set_alpn_protocols(["http/1.1"])
    return context
