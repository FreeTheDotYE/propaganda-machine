#!/usr/bin/env python3
"""Refresh the observed .gov.ye inventory and select every reachable web host."""

from __future__ import annotations

import csv
import json
import re
import ssl
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


USER_AGENT = (
    "FreeTheDotYE-ArchiveBot/1.0 "
    "(+https://github.com/FreeTheDotYE/propaganda-machine)"
)
HOST_RE = re.compile(
    r"(?i)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+gov\.ye"
)
SOURCE_TIMEOUT = 60
PROBE_TIMEOUT = 8
COMMON_CRAWL_INDEXES = 12


def request_bytes(url: str, timeout: int = SOURCE_TIMEOUT) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,*/*"},
    )
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        return response.read()


def normalize_host(value: str) -> str | None:
    host = value.strip().lower().rstrip(".")
    if host.startswith("*."):
        host = host[2:]
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if len(host) > 253 or not (host == "gov.ye" or host.endswith(".gov.ye")):
        return None
    labels = host.split(".")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not re.fullmatch(r"[a-z0-9-]+", label)
        for label in labels
    ):
        return None
    return host


def load_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        value = raw_line.split("#", 1)[0].strip()
        if value:
            values.append(value)
    return values


def add_host(host: str, source: str, discovered: dict[str, set[str]]) -> None:
    normalized = normalize_host(host)
    if normalized:
        discovered[normalized].add(source)


def collect_common_crawl() -> tuple[dict[str, set[str]], list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    errors: list[str] = []
    try:
        collections = json.loads(
            request_bytes("https://index.commoncrawl.org/collinfo.json").decode("utf-8")
        )
        index_names = [item["id"] for item in collections[:COMMON_CRAWL_INDEXES]]
    except Exception as exc:  # best-effort public source
        return found, [f"common-crawl-index-list: {exc}"]

    def query_index(index_name: str) -> tuple[str, bytes]:
        params = urlencode(
            {
                "url": "gov.ye",
                "output": "json",
                "matchType": "domain",
                "filter": ["status:200", "mime:text/html"],
                "collapse": "urlkey",
                "limit": "10000",
            },
            doseq=True,
        )
        url = f"https://index.commoncrawl.org/{index_name}-index?{params}"
        return index_name, request_bytes(url)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(query_index, name): name for name in index_names}
        for future in as_completed(futures):
            index_name = futures[future]
            try:
                _, payload = future.result()
                for line in payload.decode("utf-8", errors="replace").splitlines():
                    try:
                        record = json.loads(line)
                        add_host(urlsplit(record.get("url", "")).hostname or "", "common-crawl", found)
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception as exc:  # best-effort public source
                errors.append(f"common-crawl-{index_name}: {exc}")
    return found, errors


def collect_hackertarget() -> tuple[dict[str, set[str]], list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    try:
        payload = request_bytes("https://api.hackertarget.com/hostsearch/?q=gov.ye")
        for line in payload.decode("utf-8", errors="replace").splitlines():
            add_host(line.split(",", 1)[0], "hackertarget", found)
        return found, []
    except Exception as exc:  # best-effort public source
        return found, [f"hackertarget: {exc}"]


def collect_rapiddns() -> tuple[dict[str, set[str]], list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    try:
        payload = request_bytes("https://rapiddns.io/subdomain/gov.ye?full=1")
        for match in HOST_RE.findall(payload.decode("utf-8", errors="replace")):
            add_host(match, "rapiddns", found)
        return found, []
    except Exception as exc:  # best-effort public source
        return found, [f"rapiddns: {exc}"]


def collect_crtsh() -> tuple[dict[str, set[str]], list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    try:
        payload = request_bytes("https://crt.sh/?Identity=%25.gov.ye&output=json")
        records = json.loads(payload.decode("utf-8"))
        for record in records:
            names = [record.get("common_name", ""), record.get("name_value", "")]
            for value in names:
                for host in str(value).splitlines():
                    add_host(host, "certificate-transparency", found)
        return found, []
    except Exception as exc:  # best-effort public source
        return found, [f"certificate-transparency: {exc}"]


def probe_host(host: str) -> dict[str, str | int]:
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    failures: list[str] = []
    context = ssl._create_unverified_context()
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}/"
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,*/*",
                "Range": "bytes=0-1023",
            },
        )
        try:
            with urlopen(request, timeout=PROBE_TIMEOUT, context=context) as response:
                response.read(1024)
                return {
                    "checked_at": checked_at,
                    "host": host,
                    "selected_url": url,
                    "final_url": response.geturl(),
                    "http_status": response.status,
                    "content_type": response.headers.get_content_type(),
                    "error": "",
                }
        except HTTPError as exc:
            return {
                "checked_at": checked_at,
                "host": host,
                "selected_url": url,
                "final_url": exc.geturl(),
                "http_status": exc.code,
                "content_type": exc.headers.get_content_type() if exc.headers else "",
                "error": str(exc.reason),
            }
        except (URLError, TimeoutError, OSError) as exc:
            failures.append(f"{scheme}: {getattr(exc, 'reason', exc)}")
    return {
        "checked_at": checked_at,
        "host": host,
        "selected_url": "",
        "final_url": "",
        "http_status": 0,
        "content_type": "",
        "error": " | ".join(failures),
    }


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "usage: discover_govye.py FIXED_SITES EXISTING_DOMAINS "
            "TARGETS_OUTPUT DOMAINS_OUTPUT REPORT_OUTPUT",
            file=sys.stderr,
        )
        return 2

    fixed_sites_path = Path(sys.argv[1])
    existing_domains_path = Path(sys.argv[2])
    targets_output = Path(sys.argv[3])
    domains_output = Path(sys.argv[4])
    report_output = Path(sys.argv[5])

    discovered: dict[str, set[str]] = defaultdict(set)
    for host in load_lines(existing_domains_path):
        add_host(host, "inventory", discovered)

    fixed_sites = load_lines(fixed_sites_path)
    for url in fixed_sites:
        add_host(urlsplit(url).hostname or "", "pinned", discovered)

    source_collectors = [
        collect_common_crawl,
        collect_hackertarget,
        collect_rapiddns,
        collect_crtsh,
    ]
    source_errors: list[str] = []
    with ThreadPoolExecutor(max_workers=len(source_collectors)) as pool:
        futures = [pool.submit(collector) for collector in source_collectors]
        for future in as_completed(futures):
            hosts, errors = future.result()
            source_errors.extend(errors)
            for host, sources in hosts.items():
                discovered[host].update(sources)

    hosts = sorted(discovered)
    with ThreadPoolExecutor(max_workers=min(32, max(1, len(hosts)))) as pool:
        probe_results = list(pool.map(probe_host, hosts))

    fixed_non_gov: list[str] = []
    for url in fixed_sites:
        host = normalize_host(urlsplit(url).hostname or "")
        if host is None:
            fixed_non_gov.append(url)

    reachable = [
        result for result in probe_results if int(result["http_status"]) != 0
    ]
    target_urls = fixed_non_gov + [str(result["selected_url"]) for result in reachable]
    target_urls = list(dict.fromkeys(target_urls))

    for output in (targets_output, domains_output, report_output):
        output.parent.mkdir(parents=True, exist_ok=True)

    targets_output.write_text(
        "".join(f"{url}\n" for url in target_urls), encoding="utf-8"
    )
    domains_output.write_text(
        "# Observed .gov.ye domains; reachability is tested on every run.\n"
        + "".join(f"{host}\n" for host in hosts),
        encoding="utf-8",
    )

    fields = [
        "checked_at",
        "host",
        "selected_url",
        "final_url",
        "http_status",
        "content_type",
        "sources",
        "error",
    ]
    with report_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in probe_results:
            row = dict(result)
            row["sources"] = ";".join(sorted(discovered[str(result["host"])]))
            writer.writerow(row)

    for error in source_errors:
        print(f"source warning: {error}", file=sys.stderr)
    print(
        f"observed {len(hosts)} .gov.ye domains; "
        f"{len(reachable)} returned HTTP; {len(target_urls)} total archive targets"
    )
    return 0 if target_urls else 1


if __name__ == "__main__":
    raise SystemExit(main())
