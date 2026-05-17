#!/usr/bin/env python3
"""Convert a local PDF to Markdown with the MinerU API v4."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://mineru.net/api/v4"
DEFAULT_MODEL_VERSION = "vlm"


class MinerUError(RuntimeError):
    pass


def request_json(
    method: str,
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MinerUError(f"MinerU HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MinerUError(f"MinerU request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MinerUError(f"MinerU returned non-JSON response: {body[:500]}") from exc
    if not isinstance(parsed, dict):
        raise MinerUError("MinerU returned an unexpected JSON shape")
    if parsed.get("code") not in (0, None):
        raise MinerUError(f"MinerU API error: {json.dumps(parsed, ensure_ascii=False)[:1000]}")
    return parsed


def upload_file(upload_url: str, pdf_path: Path, *, timeout: int = 300) -> None:
    parsed = urllib.parse.urlsplit(upload_url)
    body = pdf_path.read_bytes()
    path = urllib.parse.urlunsplit(("", "", parsed.path, parsed.query, ""))
    connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_cls(parsed.netloc, timeout=timeout)
    try:
        connection.putrequest("PUT", path)
        connection.putheader("Host", parsed.netloc)
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        detail = response.read().decode("utf-8", errors="replace")
        if response.status not in (200, 201):
            raise MinerUError(f"Upload HTTP {response.status}: {detail}")
    except OSError as exc:
        raise MinerUError(f"Upload failed: {exc}") from exc
    finally:
        connection.close()


def download(url: str, destination: Path, *, timeout: int = 300) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            destination.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MinerUError(f"Download HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MinerUError(f"Download failed: {exc.reason}") from exc


def require_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise MinerUError(f"MinerU response missing data object: {json.dumps(response, ensure_ascii=False)[:800]}")
    return data


def create_upload_batch(base_url: str, api_key: str, pdf_path: Path, model_version: str) -> tuple[str, str]:
    payload = {
        "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
        "model_version": model_version,
    }
    response = request_json("POST", f"{base_url.rstrip('/')}/file-urls/batch", api_key, payload=payload)
    data = require_data(response)
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls")
    if not batch_id or not isinstance(file_urls, list) or not file_urls:
        raise MinerUError(f"Could not find batch_id/file_urls: {json.dumps(response, ensure_ascii=False)[:1000]}")
    return str(batch_id), str(file_urls[0])


def poll_batch_result(
    base_url: str,
    api_key: str,
    batch_id: str,
    pdf_name: str,
    poll_interval: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    result_url = f"{base_url.rstrip('/')}/extract-results/batch/{urllib.parse.quote(batch_id)}"

    while time.monotonic() < deadline:
        response = request_json("GET", result_url, api_key)
        data = require_data(response)
        results = data.get("extract_result")
        if not isinstance(results, list) or not results:
            raise MinerUError(f"MinerU batch result missing extract_result: {json.dumps(response, ensure_ascii=False)[:1000]}")

        result = next((item for item in results if isinstance(item, dict) and item.get("file_name") == pdf_name), results[0])
        state = str(result.get("state") or "").lower()
        if state == "done":
            return response
        if state == "failed":
            raise MinerUError(f"MinerU task failed: {json.dumps(result, ensure_ascii=False)[:1000]}")

        progress = result.get("extract_progress")
        suffix = f"; progress={progress}" if progress else ""
        print(f"Waiting for MinerU batch {batch_id}; state={state or 'unknown'}{suffix}", file=sys.stderr)
        time.sleep(poll_interval)

    raise MinerUError(f"Timed out waiting for MinerU batch {batch_id}")


def extract_full_zip_url(batch_result: dict[str, Any], pdf_name: str) -> str:
    data = require_data(batch_result)
    results = data.get("extract_result")
    if not isinstance(results, list):
        raise MinerUError(f"MinerU batch result missing extract_result: {json.dumps(batch_result, ensure_ascii=False)[:1000]}")
    result = next((item for item in results if isinstance(item, dict) and item.get("file_name") == pdf_name), results[0])
    if not isinstance(result, dict) or not result.get("full_zip_url"):
        raise MinerUError(f"Task completed, but no full_zip_url was found: {json.dumps(batch_result, ensure_ascii=False)[:1000]}")
    return str(result["full_zip_url"])


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    base = extract_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if not str(target).startswith(str(base)):
                raise MinerUError(f"Refusing unsafe zip member: {member.filename}")
        archive.extractall(extract_dir)


def find_markdown(extract_dir: Path, pdf_path: Path) -> Path:
    markdown_files = sorted(extract_dir.rglob("*.md"))
    if not markdown_files:
        raise MinerUError(f"No Markdown file found after extracting MinerU zip: {extract_dir}")
    preferred = [path for path in markdown_files if path.stem.lower() == pdf_path.stem.lower()]
    return preferred[0] if preferred else markdown_files[0]


def convert(pdf_path: Path, out_dir: Path) -> Path:
    api_key = os.environ.get("MINERU_API_KEY")
    if not api_key:
        raise MinerUError("Set MINERU_API_KEY before running this script")

    base_url = os.environ.get("MINERU_API_BASE_URL", DEFAULT_BASE_URL)
    model_version = os.environ.get("MINERU_MODEL_VERSION", DEFAULT_MODEL_VERSION)
    poll_interval = int(os.environ.get("MINERU_POLL_INTERVAL", "5"))
    timeout_seconds = int(os.environ.get("MINERU_TIMEOUT", "900"))

    out_dir.mkdir(parents=True, exist_ok=True)
    batch_id, upload_url = create_upload_batch(base_url, api_key, pdf_path, model_version)
    print(f"Created MinerU upload batch: {batch_id}", file=sys.stderr)

    upload_file(upload_url, pdf_path)
    print("Uploaded PDF", file=sys.stderr)

    result = poll_batch_result(base_url, api_key, batch_id, pdf_path.name, poll_interval, timeout_seconds)
    result_path = out_dir / "mineru_batch_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    zip_url = extract_full_zip_url(result, pdf_path.name)
    zip_path = out_dir / f"{pdf_path.stem}.mineru.zip"
    download(zip_url, zip_path)

    extract_dir = out_dir / "mineru_extract"
    safe_extract_zip(zip_path, extract_dir)
    return find_markdown(extract_dir, pdf_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a local PDF paper to Markdown with MinerU API v4")
    parser.add_argument("pdf", type=Path, help="Path to the PDF paper")
    parser.add_argument("--out", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2
    if pdf_path.suffix.lower() != ".pdf":
        print(f"Expected a PDF file: {pdf_path}", file=sys.stderr)
        return 2

    out_dir = (args.out or Path("outputs") / pdf_path.stem).resolve()
    try:
        markdown_path = convert(pdf_path, out_dir)
    except (MinerUError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


