from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from tqdm import tqdm

from phase1.lib.chunking import chunk_document
from phase1.lib.fetching import FetchResult, fetch_html, fetch_pdf
from phase1.lib.html_parse import parse_html_document, discover_first_pdf_url
from phase1.lib.normalize import normalize_document
from phase1.lib.pdf_parse import parse_pdf_document
from phase1.lib.util import (
    ensure_dir,
    iso_now,
    json_dumps,
    sanitize_filename,
    sha256_bytes,
    sha256_text,
)


@dataclass(frozen=True)
class Source:
    source_id: str
    type: str
    url: str
    label: str


def _load_sources(config_path: Path) -> List[Source]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    out: List[Source] = []
    for s in sources:
        out.append(
            Source(
                source_id=str(s["source_id"]),
                type=str(s["type"]),
                url=str(s["url"]),
                label=str(s.get("label", s["source_id"])),
            )
        )
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json_dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json_dumps(r))
            f.write("\n")


def _raw_paths(data_dir: Path, source_id: str) -> Dict[str, Path]:
    raw_dir = data_dir / "raw" / source_id
    ensure_dir(raw_dir)
    return {
        "dir": raw_dir,
        "html": raw_dir / "page.html",
        "pdf": raw_dir / "document.pdf",
        "meta": raw_dir / "fetch.json",
    }


def _out_paths(data_dir: Path, source_id: str) -> Dict[str, Path]:
    parsed_dir = data_dir / "parsed" / source_id
    chunks_dir = data_dir / "chunks" / source_id
    ensure_dir(parsed_dir)
    ensure_dir(chunks_dir)
    return {
        "parsed_dir": parsed_dir,
        "chunks_dir": chunks_dir,
        "document_json": parsed_dir / "document.json",
        "chunks_jsonl": chunks_dir / "chunks.jsonl",
    }


def _fetch_and_parse_source(
    *,
    source: Source,
    data_dir: Path,
    user_agent: str,
    timeout_s: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns: (document, chunks)
    """
    raw = _raw_paths(data_dir, source.source_id)
    out = _out_paths(data_dir, source.source_id)

    base_meta: Dict[str, Any] = {
        "source_id": source.source_id,
        "label": source.label,
        "type": source.type,
        "requested_url": source.url,
        "fetched_at": iso_now(),
    }

    if source.type == "html":
        fr: FetchResult = fetch_html(source.url, user_agent=user_agent, timeout_s=timeout_s)
        raw["html"].write_text(fr.text, encoding="utf-8")
        _write_json(raw["meta"], {**base_meta, **fr.meta, "raw_sha256": sha256_text(fr.text)})

        doc = parse_html_document(
            html=fr.text,
            url=source.url,
            source_id=source.source_id,
            label=source.label,
        )
    elif source.type == "pdf":
        fr = fetch_pdf(source.url, user_agent=user_agent, timeout_s=timeout_s)
        raw["pdf"].write_bytes(fr.content)
        _write_json(raw["meta"], {**base_meta, **fr.meta, "raw_sha256": sha256_bytes(fr.content)})

        doc = parse_pdf_document(
            pdf_bytes=fr.content,
            url=source.url,
            source_id=source.source_id,
            label=source.label,
        )
    elif source.type == "html_pdf_discover":
        fr_html = fetch_html(source.url, user_agent=user_agent, timeout_s=timeout_s)
        raw["html"].write_text(fr_html.text, encoding="utf-8")
        discovered = discover_first_pdf_url(fr_html.text, base_url=source.url)
        if not discovered:
            _write_json(
                raw["meta"],
                {
                    **base_meta,
                    **fr_html.meta,
                    "raw_sha256": sha256_text(fr_html.text),
                    "pdf_discovered": None,
                },
            )
            # Still create an HTML doc for traceability
            doc = parse_html_document(
                html=fr_html.text,
                url=source.url,
                source_id=source.source_id,
                label=source.label,
            )
        else:
            fr_pdf = fetch_pdf(discovered, user_agent=user_agent, timeout_s=timeout_s)
            raw["pdf"].write_bytes(fr_pdf.content)
            _write_json(
                raw["meta"],
                {
                    **base_meta,
                    **fr_html.meta,
                    "raw_sha256_html": sha256_text(fr_html.text),
                    "pdf_discovered": discovered,
                    **{f"pdf_{k}": v for k, v in fr_pdf.meta.items()},
                    "raw_sha256_pdf": sha256_bytes(fr_pdf.content),
                },
            )

            doc = parse_pdf_document(
                pdf_bytes=fr_pdf.content,
                url=discovered,
                source_id=source.source_id,
                label=source.label,
                parent_url=source.url,
            )
            doc.setdefault("links", {})
            doc["links"]["discovered_from"] = source.url
    else:
        raise ValueError(f"Unsupported source type: {source.type}")

    doc = normalize_document(doc)
    chunks = chunk_document(doc)

    _write_json(out["document_json"], doc)
    _write_jsonl(out["chunks_jsonl"], chunks)
    return doc, chunks


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase-1: scrape + parse + normalize + chunk")
    ap.add_argument("--config", default="phase1/sources.yaml", help="Path to sources.yaml")
    ap.add_argument("--data-dir", default="data", help="Output data directory")
    ap.add_argument("--timeout-s", type=int, default=45, help="HTTP timeout seconds")
    ap.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Phase1Scraper/1.0",
        help="HTTP User-Agent",
    )
    ap.add_argument("--limit", type=int, default=0, help="Process only first N sources (0=all)")
    args = ap.parse_args()

    config_path = Path(args.config)
    data_dir = Path(args.data_dir)
    ensure_dir(data_dir)

    sources = _load_sources(config_path)
    if args.limit and args.limit > 0:
        sources = sources[: args.limit]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_dir = data_dir / "manifests"
    ensure_dir(manifest_dir)
    manifest_path = manifest_dir / f"run_{run_id}.json"

    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "started_at": iso_now(),
        "config": str(config_path.as_posix()),
        "data_dir": str(data_dir.as_posix()),
        "sources_total": len(sources),
        "results": [],
    }

    for src in tqdm(sources, desc="Phase-1 sources"):
        try:
            doc, chunks = _fetch_and_parse_source(
                source=src,
                data_dir=data_dir,
                user_agent=args.user_agent,
                timeout_s=args.timeout_s,
            )
            manifest["results"].append(
                {
                    "source_id": src.source_id,
                    "ok": True,
                    "url": src.url,
                    "type": src.type,
                    "document_id": doc.get("document_id"),
                    "chunks": len(chunks),
                    "parsed_path": f"parsed/{src.source_id}/document.json",
                    "chunks_path": f"chunks/{src.source_id}/chunks.jsonl",
                }
            )
        except Exception as e:
            manifest["results"].append(
                {
                    "source_id": src.source_id,
                    "ok": False,
                    "url": src.url,
                    "type": src.type,
                    "error": repr(e),
                }
            )

    manifest["finished_at"] = iso_now()
    _write_json(manifest_path, manifest)
    print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

