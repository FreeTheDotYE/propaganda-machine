#!/usr/bin/env python3
"""Check every configured target and write a compact CSV status report."""

from __future__ import annotations

import csv
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = (
    "FreeTheDotYE-ArchiveBot/1.0 "
    "(+https://github.com/FreeTheDotYE/propaganda-machine)"
)


def load_sites(path: Path) -> list[str]:
    sites: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            sites.append(line)
    return sites


def check(url: str) -> dict[str, str | int]:
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,*/*",
            "Range": "bytes=0-1023",
        },
    )
    context = ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=10, context=context) as response:
            response.read(1024)
            return {
                "checked_at": checked_at,
                "url": url,
                "final_url": response.geturl(),
                "http_status": response.status,
                "content_type": response.headers.get_content_type(),
                "error": "",
            }
    except HTTPError as exc:
        return {
            "checked_at": checked_at,
            "url": url,
            "final_url": exc.geturl(),
            "http_status": exc.code,
            "content_type": exc.headers.get_content_type() if exc.headers else "",
            "error": str(exc.reason),
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "checked_at": checked_at,
            "url": url,
            "final_url": "",
            "http_status": 0,
            "content_type": "",
            "error": str(getattr(exc, "reason", exc)),
        }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_sites.py SITES_FILE OUTPUT_CSV", file=sys.stderr)
        return 2

    sites = load_sites(Path(sys.argv[1]))
    if not sites:
        print("no target sites configured", file=sys.stderr)
        return 1

    workers = min(8, len(sites))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(check, sites))

    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "checked_at",
        "url",
        "final_url",
        "http_status",
        "content_type",
        "error",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    failures = sum(1 for result in results if int(result["http_status"]) == 0)
    print(f"checked {len(results)} sites; {failures} connection failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
