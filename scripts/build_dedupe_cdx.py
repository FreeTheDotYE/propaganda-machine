#!/usr/bin/env python3
"""Build one deterministic GNU Wget CDX deduplication index from run history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_HEADER = " CDX a b a m s k r M V g u"


def parse_cdx(path: Path) -> list[tuple[tuple[str, str], str]]:
    rows: list[tuple[tuple[str, str], str]] = []
    header_fields: list[str] | None = None
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not raw.strip():
            continue
        if raw.lstrip().startswith("CDX "):
            parts = raw.split()
            if not parts or parts[0] != "CDX":
                raise ValueError(f"invalid CDX header in {path}")
            header_fields = parts[1:]
            if "a" not in header_fields or "k" not in header_fields or "u" not in header_fields:
                raise ValueError(f"CDX lacks required a/k/u fields: {path}")
            continue
        if header_fields is None:
            raise ValueError(f"CDX row precedes header: {path}")
        parts = raw.split()
        if len(parts) != len(header_fields):
            raise ValueError(f"unexpected CDX field count in {path}: {raw[:120]}")
        url_index = header_fields.index("a")
        digest_index = header_fields.index("k")
        rows.append(((parts[url_index], parts[digest_index]), raw))
    return rows


def build(history: Path, output: Path) -> dict[str, int]:
    records: dict[tuple[str, str], str] = {}
    files = [
        path
        for path in sorted(history.rglob("*.cdx"))
        if path.resolve() != output.resolve()
    ]
    for path in files:
        for key, row in parse_cdx(path):
            records[key] = row

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(DEFAULT_HEADER + "\n")
        for key in sorted(records):
            handle.write(records[key] + "\n")
    return {"cdx_files": len(files), "dedupe_records": len(records)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("history", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.history, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
