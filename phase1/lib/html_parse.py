from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from phase1.lib.util import iso_now, sha256_text


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def discover_first_pdf_url(html: str, base_url: str) -> Optional[str]:
    soup = _soup(html)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href:
            continue
        if ".pdf" in href.lower():
            return urljoin(base_url, href)
    return None


def _extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for idx, table in enumerate(soup.find_all("table")):
        rows = table.find_all("tr")
        if not rows:
            continue
        parsed_rows: List[List[str]] = []
        for tr in rows:
            cells = tr.find_all(["th", "td"])
            parsed_rows.append([_clean_text(c.get_text(" ", strip=True)) for c in cells])
        tables.append(
            {
                "index": idx,
                "rows": parsed_rows,
            }
        )
    return tables


def _extract_visible_text(soup: BeautifulSoup) -> str:
    # Remove non-content elements that create noise.
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    # Prefer <main> if present.
    main = soup.find("main")
    root = main if main else soup.body if soup.body else soup

    text = root.get_text("\n", strip=True)
    # Collapse too many blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return ""


def parse_html_document(*, html: str, url: str, source_id: str, label: str) -> Dict[str, Any]:
    soup = _soup(html)
    title = _extract_title(soup)
    text = _extract_visible_text(soup)
    tables = _extract_tables(soup)

    # Simple heuristic FAQ extraction:
    # Some pages include "FAQ" headings; try to capture nearest Q/A pairs.
    faqs: List[Dict[str, str]] = []
    for header in soup.find_all(["h2", "h3"]):
        ht = (header.get_text(" ", strip=True) or "").lower()
        if "faq" in ht or "frequently asked" in ht:
            # scan following siblings for short question lines
            sib = header.find_next()
            seen = 0
            while sib and seen < 80:
                seen += 1
                if sib.name in ("h2", "h3"):
                    break
                # many sites use accordions/buttons for questions
                if sib.name in ("button", "summary", "h4", "h5"):
                    q = _clean_text(sib.get_text(" ", strip=True))
                    ans_node = sib.find_next_sibling()
                    if ans_node:
                        a = _clean_text(ans_node.get_text(" ", strip=True))
                        if q and a and len(q) <= 250 and len(a) <= 2000:
                            faqs.append({"question": q, "answer": a})
                sib = sib.find_next_sibling()
            break

    links: List[Dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(url, href)
        txt = _clean_text(a.get_text(" ", strip=True))
        if abs_url.startswith("http"):
            links.append({"text": txt[:200], "url": abs_url})

    doc = {
        "schema": "phase1.document.v1",
        "content_type": "html",
        "source_id": source_id,
        "label": label,
        "url": url,
        "document_id": f"{source_id}:{sha256_text(url)[:16]}",
        "extracted_at": iso_now(),
        "title": title,
        "text": text,
        "tables": tables,
        "faqs": faqs,
        "links": {"all": links, "pdf_first": discover_first_pdf_url(html, base_url=url)},
    }
    return doc

