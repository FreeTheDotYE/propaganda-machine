# Propaganda Machine

Propaganda Machine preserves time-stamped copies of public pages from selected
Yemeni government and news websites under `.ye`. The resulting WARC records
support source-based research into how official infrastructure and media are
used for wartime messaging, propaganda, and claims to political legitimacy.

Inclusion in the target list identifies a site for preservation. It does not,
by itself, prove a claim about a site or its operators. Analysis should cite the
specific archived record and distinguish documented facts from inference.

## What the action does

Every Sunday, and whenever manually dispatched, the workflow:

1. checks every URL in [`sites.txt`](sites.txt) and records its HTTP status;
2. finds up to 20 same-site links from each homepage;
3. archives the homepage, those links, and same-host page assets as compressed
   WARC files;
4. generates CDX indexes, a run manifest, and SHA-256 checksums; and
5. publishes the files as assets on a dated GitHub Release.

The crawler accesses public, unauthenticated HTTP resources only. It does not
attempt logins, evade access controls, or crawl other hosts. `robots.txt`
filtering and crawl delays are disabled; the explicit page, size, host, and time
limits remain in force.

## Storage and runtime limits

The defaults are intentionally bounded:

- homepage plus at most 20 discovered pages per site;
- 25 MiB download quota per site;
- 30 MiB hard limit per WARC file;
- 12-minute timeout per site;
- sites processed sequentially in one standard GitHub-hosted job;
- four rolling archive releases retained; and
- no WARC binaries committed to Git history or stored as Actions artifacts.

With the current target list, the hard release maximum is 420 MiB, and the
rolling maximum is about 1.7 GiB. Real runs are normally smaller. Release
assets stay attached to this repository while the source repository remains
small and cloneable.

Limits can be adjusted in [`.github/workflows/archive.yml`](.github/workflows/archive.yml).
If the site list grows, reduce the per-site quota or retention count before
increasing the schedule frequency.

## Target inventory

The initial inventory combines the sites requested for this project with active
government hosts found in a recent public web index. It is source-controlled so
additions and removals remain reviewable. Add one homepage URL per line in
[`sites.txt`](sites.txt); blank lines and lines beginning with `#` are ignored.

Only add a target when there is a reasonable basis for classifying it as a
Yemeni government or news/media site. Prefer the canonical HTTPS homepage and
record supporting ownership evidence in the commit or pull request.

## Run locally

The same scripts used by GitHub Actions can be run on Ubuntu with Python 3 and
GNU Wget installed:

```bash
python3 scripts/check_sites.py sites.txt out/site-status.csv
bash scripts/archive.sh
```

Useful environment variables are `PAGE_LIMIT`, `SITE_SIZE_LIMIT_MIB`,
`SITE_HARD_LIMIT_MIB`, `SITE_TIMEOUT_MINUTES`, `SITES_FILE`, `OUT_DIR`, and `WORK_DIR`.

## Reading the output

- `*.warc.gz`: compressed request/response records suitable for replay or
  inspection with standard WARC tools;
- `*.cdx`: lookup index produced by GNU Wget;
