#!/usr/bin/env python3
"""Discover a bounded set of same-site HTML links from a homepage."""

from __future__ import annotations

import re
import ssl
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


USER_AGENT = (
    "FreeTheDotYE-ArchiveBot/1.0 "
    "(+https://github.com/FreeTheDotYE/propaganda-machine)"
)
MAX_HOMEPAGE_BYTES = 2_000_000
TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}
SKIP_EXTENSIONS = re.compile(
    r"\.(?:7z|avi|bmp|css|csv|docx?|eot|epub|gif|gz|ico|jpe?g|js|json|"
    r"m4a|mkv|mov|mp3|mp4|mpeg|ogg|otf|pdf|png|pptx?|rar|rss|svg|tar|"
    r"tiff?|tsv|ttf|txt|wav|webm|webp|woff2?|xlsx?|xml|zip)$",
    re.IGNORECASE,
)
SKIP_PATHS = re.compile(
    r"/(?:admin|login|logout|register|search|wp-admin|wp-json)(?:/|$)",
    re.IGNORECASE,
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value.strip())
                break


def comparable_host(host: str | None) -> str:
    value = (host or "").lower().rstrip(".")
    return value[4:] if value.startswith("www.") else value


def clean_link(raw: str, base_url: str, site_host: str) -> str | None:
    if not raw or raw.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None

    absolute = urljoin(base_url, raw)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username or parts.password:
        return None
    if comparable_host(parts.hostname) != comparable_host(site_host):
        return None

    path = parts.path or "/"
    if SKIP_EXTENSIONS.search(path) or SKIP_PATHS.search(path):
        return None

    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    if len(query_pairs) > 4:
        return None
    query_pairs = [
        (key, value)
        for key, value in query_pairs
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]

    netloc = parts.hostname.lower()
    if parts.port and not (
        (parts.scheme == "http" and parts.port == 80)
        or (parts.scheme == "https" and parts.port == 443)
    ):
        netloc = f"{netloc}:{parts.port}"

    return urlunsplit(
        (parts.scheme, netloc, path, urlencode(query_pairs, doseq=True), "")
    )


def discover(homepage: str, extra_page_limit: int) -> list[str]:
    request = Request(homepage, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=30, context=context) as response:
        final_home = response.geturl()
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read(MAX_HOMEPAGE_BYTES)

    if content_type not in {"text/html", "application/xhtml+xml"}:
        raise RuntimeError(f"homepage is not HTML: {content_type}")

    parser = LinkParser()
    parser.feed(body.decode(charset, errors="replace"))

    final_parts = urlsplit(final_home)
    original_parts = urlsplit(homepage)
    if comparable_host(final_parts.hostname) != comparable_host(original_parts.hostname):
        raise RuntimeError(
            f"homepage redirected to a different host: {final_parts.hostname}"
        )
    normalized_home = clean_link(final_home, final_home, final_parts.hostname or "")
    if normalized_home is None:
        raise RuntimeError("redirected homepage is outside the original HTTP site")

    selected = [normalized_home]
    seen = {normalized_home}
    for raw_link in parser.links:
        candidate = clean_link(raw_link, final_home, final_parts.hostname or "")
        if candidate is None or candidate in seen:
            continue
        seen.add(candidate)
        selected.append(candidate)
        if len(selected) >= extra_page_limit + 1:
            break

    return selected


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: discover.py HOMEPAGE EXTRA_PAGE_LIMIT OUTPUT_FILE", file=sys.stderr)
        return 2

    homepage = sys.argv[1]
    limit = int(sys.argv[2])
    output = Path(sys.argv[3])
    if limit < 0 or limit > 100:
        raise ValueError("EXTRA_PAGE_LIMIT must be between 0 and 100")

    urls = discover(homepage, limit)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(f"{url}\n" for url in urls), encoding="utf-8")
    print(f"discovered {len(urls) - 1} internal pages from {homepage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
