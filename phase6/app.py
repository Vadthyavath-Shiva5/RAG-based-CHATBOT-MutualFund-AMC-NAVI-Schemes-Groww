#!/usr/bin/env python3
"""
Phase 6 frontend static server.
Serves UI assets and injects backend API base URL for the browser client.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from flask import Flask, Response, jsonify, request, send_from_directory
from urllib import error as url_error
from urllib import request as url_request


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")


@app.get("/")
def index() -> Response:
    index_path = STATIC_DIR / "index.html"
    html = index_path.read_text(encoding="utf-8")
    backend_url = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000").rstrip("/")
    injected = f'<script>window.BACKEND_API_BASE_URL = "{backend_url}";</script>'
    html = html.replace("</head>", f"    {injected}\n</head>")
    return Response(html, mimetype="text/html")


@app.get("/<path:path>")
def static_files(path: str):
    return send_from_directory(str(STATIC_DIR), path)


def _backend_base_url() -> str:
    return os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@app.post("/api/chat")
def api_chat_proxy():
    backend_url = f"{_backend_base_url()}/chat"
    try:
        payload = request.get_json(silent=True) or {}
        body_bytes = json.dumps(payload).encode("utf-8")
        req = url_request.Request(
            backend_url,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with url_request.urlopen(req, timeout=30) as backend_resp:
            resp_body = backend_resp.read()
            resp_type = backend_resp.headers.get("Content-Type", "application/json")
            return Response(
                resp_body,
                status=backend_resp.status,
                content_type=resp_type,
            )
    except url_error.HTTPError as exc:
        err_body = exc.read()
        return Response(
            err_body,
            status=exc.code,
            content_type=exc.headers.get("Content-Type", "application/json"),
        )
    except (url_error.URLError, TimeoutError) as exc:
        return jsonify(
            {
                "success": False,
                "error": (
                    f"Backend API is unreachable at {_backend_base_url()}. "
                    "Start phase4/app.py and try again."
                ),
                "details": str(exc),
            }
        ), 503


@app.get("/api/sources")
def api_sources_proxy():
    backend_url = f"{_backend_base_url()}/sources"
    try:
        req = url_request.Request(backend_url, method="GET")
        with url_request.urlopen(req, timeout=20) as backend_resp:
            resp_body = backend_resp.read()
            resp_type = backend_resp.headers.get("Content-Type", "application/json")
            return Response(
                resp_body,
                status=backend_resp.status,
                content_type=resp_type,
            )
    except url_error.HTTPError as exc:
        err_body = exc.read()
        return Response(
            err_body,
            status=exc.code,
            content_type=exc.headers.get("Content-Type", "application/json"),
        )
    except (url_error.URLError, TimeoutError) as exc:
        return jsonify(
            {
                "success": False,
                "error": (
                    f"Backend API is unreachable at {_backend_base_url()}. "
                    "Start phase4/app.py and try again."
                ),
                "details": str(exc),
            }
        ), 503


if __name__ == "__main__":
    host = os.getenv("FRONTEND_HOST", "0.0.0.0")
    port = int(os.getenv("FRONTEND_PORT", "3000"))
    debug = os.getenv("FRONTEND_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
