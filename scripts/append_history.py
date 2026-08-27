#!/usr/bin/env python3
"""Append versioned archive metadata while preserving legacy run rows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = [
    "release", "completed_at", "targets", "warcs", "observed_govye",
    "reachable_govye", "response_records", "revisit_records",
    "metadata_version", "methodology_version", "workflow_commit",
    "methodology_sha256", "pinned_inventory_sha256",
    "accumulated_inventory_sha256", "selected_targets_sha256",
    "candidate_count", "unreachable_count", "excluded_count",
    "targets_with_records", "empty_captures", "hard_limit_fallbacks",
    "complete_failures", "clean_wget_outcomes", "non_clean_wget_outcomes",
    "warc_bytes",
]


def append(index_path: Path, release: str, completed_at: str, metadata_path: Path) -> None:
    existing = []
    if index_path.exists():
        with index_path.open(encoding="utf-8", newline="") as stream:
            existing = list(csv.DictReader(stream))
    if any(row.get("release") == release for row in existing):
        raise ValueError(f"release already indexed: {release}")
    for row in existing:
        if not row.get("metadata_version"):
            row["metadata_version"] = "legacy-unversioned"
            row["methodology_version"] = "legacy-unversioned"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    coverage = metadata["coverage"]
    archive = metadata["archive"]
    hashes = metadata["sha256"]
    existing.append({
        "release": release,
        "completed_at": completed_at,
        "targets": coverage["selected_targets"],
        "warcs": archive["archive_count"],
        "observed_govye": coverage["accumulated_inventory"],
        "reachable_govye": coverage["selected_candidate_hosts"],
        "response_records": archive["response_records"],
        "revisit_records": archive["revisit_records"],
        "metadata_version": metadata["metadata_schema_version"],
        "methodology_version": metadata["methodology_version"],
        "workflow_commit": metadata["run"]["workflow_commit"],
        "methodology_sha256": hashes["methodology"],
        "pinned_inventory_sha256": hashes["pinned_inventory"],
        "accumulated_inventory_sha256": hashes["accumulated_inventory"],
        "selected_targets_sha256": hashes["selected_targets"],
        "candidate_count": coverage["candidates"],
        "unreachable_count": coverage["unreachable_candidates"],
        "excluded_count": coverage["excluded_candidates"],
        "targets_with_records": coverage["targets_with_records"],
        "empty_captures": coverage["empty_captures"],
        "hard_limit_fallbacks": coverage["hard_limit_fallbacks"],
        "complete_failures": coverage["complete_failures"],
        "clean_wget_outcomes": archive["clean_wget_outcomes"],
        "non_clean_wget_outcomes": archive["non_clean_wget_outcomes"],
        "warc_bytes": archive["warc_bytes"],
    })
    with index_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in FIELDS}
            for row in existing
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("release")
    parser.add_argument("completed_at")
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args()
    append(args.index, args.release, args.completed_at, args.metadata)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
