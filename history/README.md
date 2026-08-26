# Permanent archive history

Each directory below this path represents one immutable archive release. It
keeps the release manifest, target inventory, discovery and status reports,
checksums, and every CDX index in Git even when the much larger WARC files are
stored as release assets.

The archive workflow never removes an archive release. Before each crawl it
combines the historical CDX records into a deterministic deduplication index.
GNU Wget uses that index to write WARC revisit records for payloads it has seen
before instead of storing the same response bytes again. Changed and newly
observed response payloads remain in the new WARC files.

`index.csv` is the compact run-level catalog. A release directory is not
rewritten after publication.
