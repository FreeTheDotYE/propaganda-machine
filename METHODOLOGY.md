# Archive methodology

Methodology version: **2.0.0**

Each run starts with the retained observed `.gov.ye` inventory, combines it
with current public discovery results, and records every candidate in
`govye-discovery.csv`. Candidates are selected only when an external
GitHub-hosted runner receives public HTML without an excluded service,
outside redirect, or error. Pinned government, media, and related targets are
then merged into the exact `targets.txt` used for capture.

Every selected target receives a bounded Wget capture. The manifest records
the target, queued pages, archive filename, Wget outcome, bytes, discovery
fallback, and response/revisit record counts. Existing historical CDX indexes
enable WARC revisit records for unchanged payloads. Oversized captures receive
one homepage-only fallback; complete failures remain explicit.

`run-metadata.json` binds each release to this methodology, the workflow
commit, pinned inventory, accumulated inventory, discovery report, manifest,
and exact target list by SHA-256. Its coverage totals are reconciled against
the CSV files and WARC files before checksums and release publication.

The runner is an external vantage outside Yemen. A failed probe does not prove
global downtime or a particular cause. DNS, TLS, application errors, rate
limiting, and filtering of traffic from outside Yemen are all possible and
require corroboration.
