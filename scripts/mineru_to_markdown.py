#!/usr/bin/env python3
"""Convert a PDF to Markdown with the MinerU API.

This script intentionally keeps the API boundary in one place so the skill can be
updated if MinerU changes its upload/task/download contract.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://mineru.net/api/v4"


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
    return parsed


def upload_file(upload_url: str, pdf_path: Path, *, timeout: int = 300) -> None:
    request = urllib.request.Request(upload_url, data=pdf_path.read_bytes(), method="PUT")
    request.add_header("Content-Type", "application/pdf")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status >= 400:
                raise MinerUError(f"Upload failed with HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MinerUError(f"Upload HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MinerUError(f"Upload failed: {exc.reason}") from exc


def download(url: str, destination: Path, *, timeout: int = 300) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            destination.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MinerUError(f"Download HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MinerUError(f"Download failed: {exc.reason}") from exc


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    nested = data.get("data")
    if isinstance(nested, dict):
        for key in keys:
            if key in nested and nested[key] not in (None, ""):
                return nested[key]
    return None


def create_task(base_url: str, api_key: str, pdf_path: Path) -> tuple[str, str | None]:
    payload = {
        "file_name": pdf_path.name,
        "parse_method": "auto",
        "is_ocr": True,
        "output_format": "markdown",
    }
    response = request_json("POST", f"{base_url.rstrip('/')}/extract/task", api_key, payload=payload)
    task_id = first_present(response, "task_id", "id")
    upload_url = first_present(response, "upload_url", "file_upload_url", "url")
    if not task_id:
        raise MinerUError(f"Could not find task id in response: {json.dumps(response, ensure_ascii=False)[:800]}")
    return str(task_id), None if upload_url is None else str(upload_url)


def poll_task(base_url: str, api_key: str, task_id: str, poll_interval: int, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    status_url = f"{base_url.rstrip('/')}/extract/task/{urllib.parse.quote(task_id)}"

    while time.monotonic() < deadline:
        response = request_json("GET", status_url, api_key)
        status = str(first_present(response, "status", "state") or "").lower()
        if status in {"done", "finished", "success", "completed"}:
            return response
        if status in {"failed", "error", "canceled", "cancelled"}:
            raise MinerUError(f"MinerU task failed: {json.dumps(response, ensure_ascii=False)[:1000]}")
        print(f"Waiting for MinerU task {task_id}; status={status or 'unknown'}", file=sys.stderr)
        time.sleep(poll_interval)

    raise MinerUError(f"Timed out waiting for MinerU task {task_id}")


def extract_markdown_url(task_result: dict[str, Any]) -> str | None:
    direct = first_present(task_result, "markdown_url", "md_url")
    if direct:
        return str(direct)

    data = task_result.get("data")
    candidates: list[Any] = []
    if isinstance(data, dict):
        candidates.extend(data.values())
    candidates.extend(task_result.values())

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.lower().endswith(".md"):
            return candidate
        if isinstance(candidate, dict):
            value = first_present(candidate, "markdown_url", "md_url", "url")
            if value and str(value).lower().endswith(".md"):
                return str(value)
    return None


def convert(pdf_path: Path, out_dir: Path) -> Path:
    api_key = os.environ.get("MINERU_API_KEY")
    if not api_key:
        raise MinerUError("Set MINERU_API_KEY before running this script")

    base_url = os.environ.get("MINERU_API_BASE_URL", DEFAULT_BASE_URL)
    poll_interval = int(os.environ.get("MINERU_POLL_INTERVAL", "5"))
    timeout_seconds = int(os.environ.get("MINERU_TIMEOUT", "900"))

    out_dir.mkdir(parents=True, exist_ok=True)
    task_id, upload_url = create_task(base_url, api_key, pdf_path)
    print(f"Created MinerU task: {task_id}", file=sys.stderr)

    if upload_url:
        upload_file(upload_url, pdf_path)
        print("Uploaded PDF", file=sys.stderr)
    else:
        print("No upload URL returned; assuming MinerU accepted the file by task creation", file=sys.stderr)

    result = poll_task(base_url, api_key, task_id, poll_interval, timeout_seconds)
    result_path = out_dir / "mineru_task_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_url = extract_markdown_url(result)
    if not markdown_url:
        raise MinerUError(f"Task completed, but no Markdown URL was found. Saved response to {result_path}")

    markdown_path = out_dir / f"{pdf_path.stem}.md"
    download(markdown_url, markdown_path)
    return markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a PDF paper to Markdown with MinerU")
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
    except MinerUError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
