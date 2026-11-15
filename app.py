"""Minimal zero-dependency WSGI entrypoint for Vercel Sprint 0 status page."""

from __future__ import annotations

from pathlib import Path

HTML_PATH = Path(__file__).resolve().parent / "index.html"


def app(environ, start_response):
    """Serve the Sprint 0 status page (index.html) at any route."""
    body = HTML_PATH.read_bytes()
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]
