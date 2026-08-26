# Propaganda Machine

Propaganda Machine preserves time-stamped public-web evidence from Yemen's
`.ye` government, media, and related infrastructure. The WARC records support research
into how this national namespace is used for wartime messaging, propaganda,
and claims to political legitimacy.

## Houthi control of the namespace

**All `.gov.ye` sites captured by this project operate inside a governmental
namespace run under Houthi militia control. This project therefore classifies
the `.gov.ye` publication infrastructure as Houthi-operated, including where an
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

Every Sunday, and whenever manually dispatched, the workflow:

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
   WARC files; and
8. publishes WARC files, CDX indexes, discovery/status reports, a manifest, and
   SHA-256 checksums as assets on a dated GitHub Release.

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
- four rolling archive releases retained; and
- no WARC binaries stored as Actions artifacts.

The hard maximum for one release is `12 MiB × reachable target count`; the
latest target count is recorded in [`LATEST.md`](LATEST.md). Release assets stay
attached to this repository while the Git repository remains small and
cloneable.

Limits can be adjusted in [`.github/workflows/archive.yml`](.github/workflows/archive.yml).
If the reachable inventory grows substantially, reduce the per-site quota or
retention count before increasing schedule frequency.

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

Timestamps are UTC. Automated captures can be incomplete because a site is
offline, blocks the GitHub runner, relies on client-side rendering, or exceeds a
cap. The reports retain those failures instead of silently dropping them.

## License

The automation code is released under the MIT License. Copyright and other
rights in archived third-party material remain with their respective owners.
