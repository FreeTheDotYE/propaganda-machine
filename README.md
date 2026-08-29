# Propaganda Machine

Propaganda Machine preserves time-stamped public-web evidence from Yemen's
`.ye` government, media, and related sites operating within publication
infrastructure administered through institutions documented below as under
Houthi control. The WARC records support research
into how this national namespace is used for wartime messaging, propaganda,
and claims to political legitimacy.

## Houthi control of the namespace

**All .gov.ye sites captured by this project operate within the government namespace administered under Houthi authority. Other .ye targets operate within the same Houthi-controlled national registry and telecommunications environment. This project therefore classifies
the `.ye` publication infrastructure as Houthi-operated, including where an
individual page uses a ministry, authority, governorate, or other institutional
label.** The archive also includes identified Houthi media elsewhere under
`.ye`, including Saba in Arabic and English, the Military Media, Al-Thawrah,
Al-Siyasiah, Sanaa Radio, Yemen TV, and Al-Sahat TV.

The attribution is based on the control chain, not merely on page content:

- [IANA identifies TeleYemen as the manager of `.ye`](https://www.iana.org/domains/root/db/ye.html),
  with its administrative and technical contacts in Sana'a.
- [Recorded Future reported that the Houthis supervised YemenNet and controlled
  the `.ye` domain space](https://www.recordedfuture.com/research/yemen-internet-activity),
  and that official government sites were changed to reflect the Houthi
  government in Sana'a.
- In 2025, Yemen's National Organization of Yemeni Reporters
  [described YemenNet and TeleYemen as controlled by the Houthi group](https://sada-ye.org/en/sada-condemns-the-blocking-of-barran-press-website-by-yemen-net-and-teleyemen-under-houthi-control/)
  while documenting their blocking of an independent news site.

An archived response is evidence of what a server published at a given time.
Claims about a particular article, named author, or institution should still
cite the specific archived record and distinguish observation from inference.

## What the action does

Every Thursday and Saturday, and whenever manually dispatched, the workflow:

1. refreshes `.gov.ye` candidates from the twelve latest Common Crawl indexes,
   HackerTarget, RapidDNS, certificate-transparency results, and the retained
   source-controlled inventory;
2. rejects mail, webmail, cPanel, calendar/contact, nameserver, gateway,
   development, test, and other obvious infrastructure-only hostnames;
3. probes the remaining candidates over HTTPS and HTTP and selects only hosts
   serving public HTML inside `.gov.ye`, excluding HTTP errors, non-HTML
   services, outside redirects, and recognized mail/control-panel login pages;
4. adds the pinned `.ye` media and requested related sites in [`sites.txt`](sites.txt);
5. checks every selected URL and records its current HTTP status;
6. finds up to 20 same-host links from each homepage;
7. archives the homepage, those links, and same-host page assets as compressed
   WARC files, using the permanent historical CDX corpus to write revisit
   records instead of duplicating unchanged response payloads;
8. publishes WARC files, CDX indexes, discovery/status reports, a manifest, and
   SHA-256 checksums as assets on a dated GitHub Release; and
9. commits every manifest, CDX index, checksum, target list, discovery report,
   and status report permanently under [`history/`](history/).

Newly observed `.gov.ye` domains are written back to
[`govye-domains.txt`](govye-domains.txt) after a successful run. This preserves
the accumulated candidate set even when a public discovery service is
unavailable later.

No passive source can prove that it has the complete private DNS zone. In this
repository, “all accessible `.gov.ye` sites” means every hostname accumulated
from the documented sources that passed the public-HTML website filter that run.
The discovery CSV records the source and result for every candidate so coverage
is auditable rather than implied.

The crawler accesses public, unauthenticated HTTP resources only. It does not
attempt logins or evade access controls. `robots.txt` filtering and crawl delays
are disabled. Page, size, host, request, site, and job limits remain in force.

## Storage and runtime limits

The defaults keep the project inside bounded GitHub-hosted execution and avoid
putting large binaries in Git history:

- homepage plus at most 20 discovered pages per target;
- 10 MiB Wget download quota per target;
- 12 MiB hard limit per WARC file;
- 10-second network attempts with no retry;
- two-minute total timeout per target;
- sites processed sequentially in one standard GitHub-hosted job;
- 330-minute job ceiling;
- every archive release retained permanently; and
- no WARC binaries stored as Actions artifacts.

The hard maximum for one release is `12 MiB × reachable target count`; the
latest target count is recorded in [`LATEST.md`](LATEST.md). Changed and newly
seen response payloads are stored normally. When Wget finds an exact URL and
payload-digest match in the historical CDX corpus, it writes a standards-based
WARC revisit record instead of another copy of the response bytes. The original
WARC remains available because archive releases are not rotated away.

Run metadata and CDX files remain in Git for durable discovery. The larger WARC
files stay attached to their dated releases so the repository remains
cloneable. [`history/index.csv`](history/index.csv) is the compact permanent run
catalog.

Limits can be adjusted in [`.github/workflows/archive.yml`](.github/workflows/archive.yml).
If the reachable inventory grows substantially, reduce the per-site quota or
page limit before increasing schedule frequency.

## Inventory files

- [`govye-domains.txt`](govye-domains.txt) is the accumulated `.gov.ye`
  candidate inventory. Every entry is reprobed on every run.
- [`sites.txt`](sites.txt) pins known government examples, `.ye` media,
  and explicitly requested related sites. Government entries are merged into
  the candidate inventory; non-government entries remain archive targets.
- `out/targets.txt` is generated during a run and contains only reachable
  `.gov.ye` sites plus pinned non-government targets.

## Run locally

The same scripts used by GitHub Actions can be run on Ubuntu with Python 3 and
GNU Wget installed:

```bash
python3 scripts/discover_govye.py sites.txt govye-domains.txt \
  out/targets.txt out/govye-domains.txt out/govye-discovery.csv
python3 scripts/check_sites.py out/targets.txt out/site-status.csv
SITES_FILE=out/targets.txt bash scripts/archive.sh
```

Useful environment variables are `PAGE_LIMIT`, `SITE_SIZE_LIMIT_MIB`,
`SITE_HARD_LIMIT_MIB`, `SITE_TIMEOUT_MINUTES`, `SITES_FILE`, `OUT_DIR`, and
`WORK_DIR`.

## Reading the output

- `*.warc.gz`: compressed HTTP request/response records;
- `*.cdx`: lookup indexes produced by GNU Wget;
- `govye-discovery.csv`: every observed `.gov.ye` host, its discovery sources,
  selected protocol, reachability, redirect target, and HTTP status;
- `targets.txt`: exact URLs selected for that run;
- `site-status.csv`: second reachability check for every selected target;
- `manifest.csv`: per-target crawl result, queued-page count, and archive size;
  and
- `SHA256SUMS`: integrity hashes for all WARC files.

Timestamps are UTC. The collector runs from an external GitHub-hosted vantage.
A failed request from that runner does not prove that a site is globally down.
It may reflect DNS, TLS, or application failure, rate limiting, client-side
rendering, a capture cap, or traffic being restricted outside Yemen. Filtering
in networks under Houthi control is one hypothesis for an outside-only failure,
not a conclusion that can be drawn from one probe. Corroboration from Yemeni
and other independent vantage points is required before attributing a failure
to a firewall or operator action. The reports retain failures instead of
silently dropping them.

## License

The automation code is released under the MIT License. Copyright and other
rights in archived third-party material remain with their respective owners.
