#!/usr/bin/env python3
"""Build and reconcile versioned metadata for one WARC release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


VERSION = "2.0.0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def target_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def integer(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    if not value.isdigit():
        raise ValueError(f"invalid integer in manifest: {key}={value!r}")
    return int(value)


def build(root: Path, out: Path, workflow_commit: str, workflow_run_id: str) -> dict:
    root = root.resolve()
    out = out.resolve()
    discovery = csv_rows(out / "govye-discovery.csv")
    manifest = csv_rows(out / "manifest.csv")
    targets = target_lines(out / "targets.txt")
    accumulated = target_lines(out / "govye-domains.txt")
    warcs = sorted(out.glob("*.warc.gz"))

    selected_candidates = sum(bool(row.get("selected_url")) for row in discovery)
    unreachable = sum(
        not row.get("selected_url") and row.get("http_status") == "0"
        for row in discovery
    )
    excluded = len(discovery) - selected_candidates - unreachable
    response_records = sum(integer(row, "response_records") for row in manifest)
    revisit_records = sum(integer(row, "revisit_records") for row in manifest)
    manifest_bytes = sum(integer(row, "bytes") for row in manifest)
    clean = sum(row.get("wget_exit_code") == "0" for row in manifest)
    hard_limit = sum("hard-limit" in row.get("result", "") for row in manifest)
    complete_failures = sum(not row.get("archive") for row in manifest)
    with_records = sum(
        integer(row, "response_records") + integer(row, "revisit_records") > 0
        for row in manifest
    )
    empty_captures = sum(
        bool(row.get("archive"))
        and integer(row, "response_records") + integer(row, "revisit_records") == 0
        for row in manifest
    )
    captured_at = manifest[0]["captured_at"] if manifest else ""
    metadata = {
        "metadata_schema_version": VERSION,
        "methodology_version": VERSION,
        "run": {
            "captured_at": captured_at,
            "workflow_commit": workflow_commit,
            "workflow_run_id": workflow_run_id,
        },
        "vantage": {
            "provider": "GitHub Actions",
            "runner": "ubuntu-latest",
            "classification": "external-public-web-vantage-outside-yemen",
        },
        "sha256": {
            "methodology": digest(root / "METHODOLOGY.md"),
            "pinned_inventory": digest(root / "sites.txt"),
            "accumulated_inventory": digest(out / "govye-domains.txt"),
            "selected_targets": digest(out / "targets.txt"),
            "discovery": digest(out / "govye-discovery.csv"),
            "manifest": digest(out / "manifest.csv"),
        },
        "coverage": {
            "candidates": len(discovery),
            "selected_candidate_hosts": selected_candidates,
            "selected_targets": len(targets),
            "accumulated_inventory": len(accumulated),
            "unreachable_candidates": unreachable,
            "excluded_candidates": excluded,
            "targets_with_records": with_records,
            "empty_captures": empty_captures,
            "hard_limit_fallbacks": hard_limit,
            "complete_failures": complete_failures,
        },
        "archive": {
            "manifest_rows": len(manifest),
            "archive_count": len(warcs),
            "warc_bytes": sum(path.stat().st_size for path in warcs),
            "manifest_bytes": manifest_bytes,
            "clean_wget_outcomes": clean,
            "non_clean_wget_outcomes": len(manifest) - clean,
            "response_records": response_records,
            "revisit_records": revisit_records,
        },
    }
    (out / "run-metadata.json").write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def write_checksums(out: Path) -> None:
    paths = sorted(
        path for path in out.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    )
    (out / "SHA256SUMS").write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in paths),
        encoding="ascii",
    )


def validate(root: Path, out: Path) -> dict:
    metadata = json.loads((out / "run-metadata.json").read_text(encoding="utf-8"))
    rebuilt_path = out / "run-metadata.json"
    checksums = {}
    for line in (out / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        value, name = line.split("  ", 1)
        if name in checksums:
            raise ValueError(f"duplicate checksum: {name}")
        checksums[name] = value
        if digest(out / name) != value:
            raise ValueError(f"checksum mismatch: {name}")
    expected_files = {
        path.name for path in out.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if set(checksums) != expected_files:
        raise ValueError("checksum inventory does not match release files")

    manifest = csv_rows(out / "manifest.csv")
    targets = target_lines(out / "targets.txt")
    warcs = sorted(out.glob("*.warc.gz"))
    archive = metadata["archive"]
    coverage = metadata["coverage"]
    if coverage["selected_targets"] != len(targets) or len(manifest) != len(targets):
        raise ValueError("target, manifest, and metadata totals differ")
    if archive["archive_count"] != len(warcs):
        raise ValueError("archive count differs from WARC files")
    if archive["warc_bytes"] != sum(path.stat().st_size for path in warcs):
        raise ValueError("WARC byte total mismatch")
    if archive["manifest_bytes"] != sum(integer(row, "bytes") for row in manifest):
        raise ValueError("manifest byte total mismatch")
    for key, path in {
        "methodology": root / "METHODOLOGY.md",
        "pinned_inventory": root / "sites.txt",
        "accumulated_inventory": out / "govye-domains.txt",
        "selected_targets": out / "targets.txt",
        "discovery": out / "govye-discovery.csv",
        "manifest": out / "manifest.csv",
    }.items():
        if metadata["sha256"][key] != digest(path):
            raise ValueError(f"metadata hash mismatch: {key}")
    if checksums.get(rebuilt_path.name) != digest(rebuilt_path):
        raise ValueError("metadata is absent from release checksums")
    return {
        "metadata_ok": True,
        "targets": len(targets),
        "warcs": len(warcs),
        "checksums": len(checksums),
        "response_records": archive["response_records"],
        "revisit_records": archive["revisit_records"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--workflow-commit", required=True)
    parser.add_argument("--workflow-run-id", default="")
    args = parser.parse_args()
    metadata = build(
        args.root, args.out, args.workflow_commit, args.workflow_run_id
    )
    write_checksums(args.out)
    print(json.dumps(validate(args.root.resolve(), args.out.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
