import gzip
import tempfile
import unittest
from pathlib import Path

from scripts.build_dedupe_cdx import DEFAULT_HEADER, build
from scripts.warc_stats import count_records


def warc_record(record_type: str, body: bytes) -> bytes:
    headers = (
        "WARC/1.0\r\n"
        f"WARC-Type: {record_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
    ).encode("ascii")
    return headers + body + b"\r\n\r\n"


class ArchiveHistoryTests(unittest.TestCase):
    def test_builds_deterministic_deduplication_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "history" / "archive-1" / "cdx" / "one.cdx"
            second = root / "history" / "archive-2" / "cdx" / "two.cdx"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text(
                DEFAULT_HEADER
                + "\nhttps://a.ye/ 20260101000000 https://a.ye/ text/html 200 sha1:AAA - - 0 one.warc.gz urn:uuid:one\n",
                encoding="utf-8",
            )
            second.write_text(
                DEFAULT_HEADER
                + "\nhttps://a.ye/ 20260201000000 https://a.ye/ text/html 200 sha1:AAA - - 0 two.warc.gz urn:uuid:two\n"
                + "https://b.ye/ 20260201000000 https://b.ye/ text/html 200 sha1:BBB - - 0 two.warc.gz urn:uuid:three\n",
                encoding="utf-8",
            )
            output = root / "work" / "dedupe.cdx"
            summary = build(root / "history", output)
            rows = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(summary, {"cdx_files": 2, "dedupe_records": 2})
            self.assertEqual(rows[0], DEFAULT_HEADER)
            self.assertIn("two.warc.gz urn:uuid:two", rows[1])
            self.assertIn("two.warc.gz urn:uuid:three", rows[2])

    def test_counts_response_and_revisit_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.warc.gz"
            with gzip.open(path, "wb") as handle:
                handle.write(warc_record("warcinfo", b"metadata"))
                handle.write(warc_record("response", b"WARC/1.0 inside payload"))
                handle.write(warc_record("revisit", b""))
            self.assertEqual(count_records(path), (1, 1))


if __name__ == "__main__":
    unittest.main()
