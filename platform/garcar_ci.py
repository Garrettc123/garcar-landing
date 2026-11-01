#!/usr/bin/env python3
"""Garcar's local, fail-closed CI runner. Standard library only; no network access."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

PLATFORM = Path(__file__).resolve().parent
ROOT = PLATFORM.parent
ARTIFACT_ROOT = PLATFORM / ".garcar-builds"
TIMEOUT_SECONDS = 900

def safe_environment() -> dict[str, str]:
    # Do not forward API keys, cloud credentials, payment secrets, or app tokens
    # from the interactive shell into build/test subprocesses.
    allowed = ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL",
               "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(description="Run Garcar's local production-line verification pipeline.")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS,
                        help="maximum seconds per stage (default: 900)")
    args = parser.parse_args()
    if args.timeout < 1 or args.timeout > 7200:
        parser.error("--timeout must be between 1 and 7200 seconds")

    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    build_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    build_dir = ARTIFACT_ROOT / build_id
    build_dir.mkdir(mode=0o700)
    python = sys.executable
    stages = [
        ("compile", [python, "-m", "py_compile", "server.py", "digital_delivery.py"], PLATFORM),
        ("unit_tests", [python, "-m", "unittest", "discover", "-s", "tests", "-v"], PLATFORM),
        ("http_smoke", [python, "smoke_test.py"], PLATFORM),
        ("catalog_validation", [python, "validate_catalog.py", "catalog.json"], ROOT / "divisions"),
    ]
    results = []
    overall_start = time.monotonic()
    print("GARCAR LOCAL CI — SAFE VERIFICATION MODE")
    print(f"Build: {build_id}")
    print(f"Host: {platform.system()} {platform.machine()} | Python: {platform.python_version()}")
    print("Network deployment, payment, email, SMS, and customer-data actions: DISABLED")
    print(f"Artifacts: {build_dir}")

    env = safe_environment()
    for name, command, cwd in stages:
        started = time.monotonic()
        print(f"\n[{len(results)+1}/{len(stages)}] {name}")
        try:
            completed = subprocess.run(command, cwd=str(cwd), env=env,
                                       capture_output=True, text=True,
                                       errors="replace", timeout=args.timeout,
                                       check=False)
            output = (completed.stdout or "") + (completed.stderr or "")
            log_path = build_dir / f"{name}.log"
            log_path.write_text(output, encoding="utf-8")
            result = {
                "stage": name,
                "status": "passed" if completed.returncode == 0 else "failed",
                "return_code": completed.returncode,
                "duration_seconds": round(time.monotonic() - started, 3),
                "log": log_path.name,
                "log_sha256": sha256(log_path),
            }
            results.append(result)
            print(output[-5000:] if output else "(no output)")
            print(f"RESULT: {result['status'].upper()}")
            if completed.returncode != 0:
                break
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") + (exc.stderr or "")) if isinstance(exc.stdout, str) else "Stage timed out."
            log_path = build_dir / f"{name}.log"
            log_path.write_text(output or "Stage timed out.", encoding="utf-8")
            results.append({"stage": name, "status": "timeout", "duration_seconds": round(time.monotonic()-started,3), "log": log_path.name, "log_sha256": sha256(log_path)})
            print("RESULT: TIMEOUT")
            break
        except OSError as exc:
            log_path = build_dir / f"{name}.log"
            log_path.write_text(f"Runner could not start stage: {type(exc).__name__}", encoding="utf-8")
            results.append({"stage": name, "status": "runner_error", "duration_seconds": round(time.monotonic()-started,3), "log": log_path.name, "log_sha256": sha256(log_path)})
            print(f"RESULT: RUNNER ERROR ({type(exc).__name__})")
            break

    passed = len(results) == len(stages) and all(item["status"] == "passed" for item in results)
    report = {
        "schema_version": 1,
        "build_id": build_id,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "result": "passed" if passed else "blocked_or_failed",
        "host": {"system": platform.system(), "machine": platform.machine(), "python": platform.python_version()},
        "repository_root": str(ROOT),
        "stages": results,
        "duration_seconds": round(time.monotonic() - overall_start, 3),
        "external_actions": {"network_deploy": False, "payments": False, "email": False, "sms": False, "customer_data": False},
    }
    report_path = build_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = []
    for path in sorted(build_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            manifest.append(f"{sha256(path)}  {path.name}")
    (build_dir / "SHA256SUMS").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"\nPIPELINE RESULT: {'PASSED' if passed else 'NOT PASSED'}")
    print(f"Report: {report_path}")
    print("A passed local pipeline is evidence for this exact local checkout only; it is not production approval.")
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
