#!/usr/bin/env python3
"""Parse ScienceDirect/Elsevier citation exports into ordered records.

The script intentionally preserves the file order because issue exports are
usually already ordered by the journal's table of contents or page/article
locator order.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def split_records(text: str) -> list[list[str]]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    return [[line.strip() for line in block.split("\n") if line.strip()] for block in blocks if block.strip()]


def clean_trailing_comma(value: str) -> str:
    return value.strip().rstrip(",").strip()


def parse_record(lines: list[str], index: int) -> dict[str, object]:
    abstract = ""
    keywords = ""
    doi = ""
    url = ""
    volume = ""
    year = ""
    locator = ""
    journal = ""
    title = ""
    authors = ""

    for line in lines:
        if line.startswith("Abstract:"):
            abstract = line.removeprefix("Abstract:").strip()
        elif line.startswith("Keywords:"):
            keywords = line.removeprefix("Keywords:").strip()
        elif line.startswith("https://doi.org/"):
            doi = clean_trailing_comma(line).rstrip(".")
        elif line.startswith("(") and "sciencedirect.com" in line:
            url = line.strip("()")

    volume_index = next((i for i, line in enumerate(lines) if line.startswith("Volume ")), None)
    if volume_index is not None:
        volume = clean_trailing_comma(lines[volume_index])
        if volume_index >= 1:
            journal = clean_trailing_comma(lines[volume_index - 1])
        if volume_index >= 2:
            title = clean_trailing_comma(lines[volume_index - 2])
            authors = " ".join(clean_trailing_comma(line) for line in lines[: volume_index - 2])
        if volume_index + 1 < len(lines):
            year = clean_trailing_comma(lines[volume_index + 1])
        if volume_index + 2 < len(lines):
            locator = clean_trailing_comma(lines[volume_index + 2])
    else:
        pre_abstract = []
        for line in lines:
            if line.startswith("Abstract:"):
                break
            pre_abstract.append(line)
        if len(pre_abstract) >= 2:
            authors = clean_trailing_comma(pre_abstract[0])
            title = clean_trailing_comma(pre_abstract[1])

    return {
        "order": index,
        "authors": authors,
        "title": title,
        "journal": journal,
        "volume": volume,
        "year": year,
        "locator": locator,
        "doi": doi,
        "url": url,
        "abstract": abstract,
        "keywords": keywords,
    }


def to_markdown(records: list[dict[str, object]]) -> str:
    lines = ["# ScienceDirect Issue Records", ""]
    for record in records:
        lines.append(f"## {record['order']}. {record.get('title') or 'Untitled'}")
        lines.append("")
        for key in ("authors", "journal", "volume", "year", "locator", "doi", "url", "keywords"):
            value = record.get(key)
            if value:
                lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append(str(record.get("abstract") or ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a ScienceDirect citation export.")
    parser.add_argument("input", type=Path, help="ScienceDirect/Elsevier citation export .txt")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--out", type=Path, help="Optional output path")
    args = parser.parse_args()

    records = [parse_record(lines, i + 1) for i, lines in enumerate(split_records(read_text(args.input)))]
    output = json.dumps(records, ensure_ascii=False, indent=2) if args.format == "json" else to_markdown(records)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
