from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    headers: Dict[str, str]
    text: str
    meta: Dict[str, Any]


@dataclass(frozen=True)
class FetchBinaryResult:
    url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    meta: Dict[str, Any]


def _session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Connection": "keep-alive",
        }
    )
    return s


def fetch_html(url: str, *, user_agent: str, timeout_s: int = 45) -> FetchResult:
    """
    Fetch HTML, using Playwright for JS-heavy sites (Groww, AMFI, SEBI), otherwise requests.
    """
    def _host_needs_js(u: str) -> bool:
        u_lower = u.lower()
        return any(h in u_lower for h in ("groww.in", "amfiindia.com", "sebi.gov.in"))

    if not _host_needs_js(url):
        s = _session(user_agent)
        r = s.get(url, timeout=timeout_s)
        r.raise_for_status()
        r.encoding = r.encoding or "utf-8"
        text = r.text
        headers = {k: v for k, v in r.headers.items()}
        meta = {
            "final_url": str(r.url),
            "status_code": int(r.status_code),
            "content_type": headers.get("Content-Type"),
            "content_length": headers.get("Content-Length"),
            "rendered_with": "requests",
        }
        return FetchResult(url=url, status_code=r.status_code, headers=headers, text=text, meta=meta)

    # JS-rendered path with Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=user_agent, viewport={"width": 1280, "height": 720})
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_s * 1000)
            # Give React/SPA a small extra settle time
            page.wait_for_timeout(2000)
            text = page.content()
            final_url = page.url
        finally:
            browser.close()

    headers: Dict[str, str] = {}
    meta = {
        "final_url": final_url,
        "status_code": 200,
        "content_type": "text/html (playwright)",
        "content_length": None,
        "rendered_with": "playwright_chromium",
    }
    return FetchResult(url=url, status_code=200, headers=headers, text=text, meta=meta)


def fetch_pdf(url: str, *, user_agent: str, timeout_s: int = 60) -> FetchBinaryResult:
    s = _session(user_agent)
    r = s.get(url, timeout=timeout_s)
    r.raise_for_status()
    headers = {k: v for k, v in r.headers.items()}
    meta = {
        "final_url": str(r.url),
        "status_code": int(r.status_code),
        "content_type": headers.get("Content-Type"),
        "content_length": headers.get("Content-Length"),
    }
    return FetchBinaryResult(url=url, status_code=r.status_code, headers=headers, content=r.content, meta=meta)

