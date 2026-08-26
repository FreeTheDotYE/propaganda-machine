#!/usr/bin/env python3
"""Count response and revisit records in a gzip-compressed WARC."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


def count_records(path: Path) -> tuple[int, int]:
    responses = 0
    revisits = 0
    with gzip.open(path, "rb") as handle:
        while True:
            line = handle.readline()
            while line in (b"\r\n", b"\n"):
                line = handle.readline()
            if not line:
                break
            if not line.startswith(b"WARC/"):
                raise ValueError(f"invalid WARC record boundary in {path}")

            headers: dict[bytes, bytes] = {}
            while True:
                line = handle.readline()
                if line in (b"\r\n", b"\n"):
                    break
                if not line:
                    raise ValueError(f"truncated WARC headers in {path}")
                name, separator, value = line.partition(b":")
                if not separator:
                    raise ValueError(f"malformed WARC header in {path}")
                headers[name.strip().lower()] = value.strip()

            try:
                content_length = int(headers[b"content-length"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"invalid WARC Content-Length in {path}") from exc
            payload = handle.read(content_length)
            if len(payload) != content_length:
                raise ValueError(f"truncated WARC payload in {path}")

            record_type = headers.get(b"warc-type", b"").lower()
            if record_type == b"response":
                responses += 1
            elif record_type == b"revisit":
                revisits += 1
    return responses, revisits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("warc", type=Path)
    args = parser.parse_args()
    responses, revisits = count_records(args.warc)
    print(f"{responses}\t{revisits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
