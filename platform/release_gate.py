#!/usr/bin/env python3
"""Fail-closed release evidence gate. Validates local CI evidence; never deploys."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

REQUIRED_STAGES = ("compile", "unit_tests", "http_smoke", "catalog_validation")

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Garcar local build evidence before release review.")
    parser.add_argument("report", help="Path to a garcar_ci.py report.json")
    args = parser.parse_args()
    report_path = Path(args.report).resolve()
    build_dir = report_path.parent
    failures: list[str] = []

    if not report_path.is_file():
        print("BLOCKED: report file does not exist.")
        return 2
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("BLOCKED: report is unreadable or invalid JSON.")
        return 2

    if report.get("schema_version") != 1:
        failures.append("unsupported report schema")
    if report.get("result") != "passed":
        failures.append("pipeline report is not marked passed")

    stages = report.get("stages")
    if not isinstance(stages, list):
        failures.append("stage list missing")
        stages = []
    actual = [item.get("stage") for item in stages if isinstance(item, dict)]
    if tuple(actual) != REQUIRED_STAGES:
        failures.append("required stages are missing, reordered, or duplicated")
    for item in stages:
        if not isinstance(item, dict) or item.get("status") != "passed" or item.get("return_code") != 0:
            failures.append("one or more stages did not pass")
            break
        log_name = item.get("log")
        if not isinstance(log_name, str) or Path(log_name).name != log_name:
            failures.append("invalid stage log reference")
            break
        log_path = build_dir / log_name
        if not log_path.is_file() or digest(log_path) != item.get("log_sha256"):
            failures.append(f"missing or mismatched stage log: {log_name}")
            break

    manifest_path = build_dir / "SHA256SUMS"
    if not manifest_path.is_file():
        failures.append("SHA256SUMS manifest missing")
    else:
        entries = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            parts = line.split("  ", 1)
            if len(parts) != 2 or Path(parts[1]).name != parts[1]:
                failures.append("malformed checksum manifest")
                break
            entries[parts[1]] = parts[0]
        for name in ("report.json", *(f"{stage}.log" for stage in REQUIRED_STAGES)):
            file_path = build_dir / name
            if name not in entries or not file_path.is_file() or digest(file_path) != entries.get(name):
                failures.append(f"checksum verification failed: {name}")

    actions = report.get("external_actions", {})
    if any(actions.get(key) is not False for key in ("network_deploy", "payments", "email", "sms", "customer_data")):
        failures.append("report does not prove all external actions were disabled")

    if failures:
        print("RELEASE GATE: BLOCKED")
        for failure in dict.fromkeys(failures):
            print(f"- {failure}")
        print("No deployment, merge, payment, or customer-facing action was performed.")
        return 1

    print("RELEASE GATE: EVIDENCE VALID")
    print(f"Build ID: {report.get('build_id', 'unknown')}")
    print("All four verification stages passed and their logs/checksums match.")
    print("This permits a human release review only; it does NOT authorize or perform deployment.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
