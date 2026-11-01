# Run Garcar Locally on Android / Termux

This guide runs the local operating console on the Android device itself. It does not deploy a public website or connect payment, email, SMS, banking, or customer systems.

## 1. Install the free tools

In Termux:

```bash
pkg update
pkg install python git -y
```

Confirm Python:

```bash
python --version
```

Python 3.10 or newer is recommended.

## 2. Download the feature branch

```bash
cd ~
git clone --depth 1 --branch build/eight-division-operating-system-20261101 https://github.com/Garrettc123/garcar-landing.git
cd ~/garcar-landing/platform
```

No GitHub token is required for this public repository. Do not put passwords or API keys into the commands.

## 3. Run the checks

```bash
bash run_checks.sh
```

The smoke test starts a temporary loopback-only server, uses a temporary database and synthetic records, then stops the server. It does not use live customer data.

If a check fails, keep the full error output. Do not proceed to production release based on a partial test result.

## 4. Start the local console

To add two clearly labeled synthetic demo leads to a new local database:

```bash
python server.py --demo
```

Or start with an empty database:

```bash
python server.py
```

The server prints a random local admin token. Keep it private. Do not paste it into a chat, commit it to GitHub, or share a screenshot containing it.

## 5. Open the console

Open this address in the Android browser on the same device:

```text
http://127.0.0.1:8788
```

Paste the token from the Termux terminal into the Local Operator Access box. The browser stores it only for the current tab session.

## 6. What you can use locally

- Record a contractor lead and track its status.
- Create an opportunity linked to one of the 46 catalog offers.
- Record voluntary product/customer discovery interviews.
- View all eight divisions and the twelve digital product previews; exercise the test-mode digital entitlement sandbox.
- Track build/release states for all 46 offers and attach evidence references.
- Enter manual inflows/outflows and calculate a 13-week cash scenario.
- Save approved internal reference text and run local keyword search.
- Create dispatch, maintenance, support-review, and shift-handoff work items.
- Record action approval requests and inspect the hash-chain audit ledger.
- Run the digital test-mode order, entitlement, protected PDF download, and refund-revocation flow.
- Run local database diagnostics and create a local backup.

## 7. Data and safety rules

- The local database and backups are not encrypted by this application. Do not enter bank credentials, card data, passwords, medical details, or sensitive customer records.
- The app is designed for one local operator. It has no production multi-user sign-in or tenant isolation.
- Keep Termux and the Android device protected. Stop the server with Ctrl+C when finished.
- The server binds to 127.0.0.1. Do not change it to 0.0.0.0 or expose the port to the internet.
- Approvals in this app record a decision only; they do not send messages, move money, or deploy software.
- Pipeline amounts are not collected revenue. Scenario outputs are not forecasts.
- The digital delivery feature is a local payment simulator only. It does not connect to a payment processor or charge a card. Private PDF files must be installed in the ignored local asset folder before download testing.
- No production deployment, customer data access, outbound message, or live payment is performed by this guide.

## 8. Update the local checkout

To fetch changes later:

```bash
cd ~/garcar-landing
git pull origin build/eight-division-operating-system-20261101
```

Review the changed files and rerun the tests before using updated code.


## 9. Run Garcar's own build pipeline

From `~/garcar-landing/platform`:

```bash
bash run_garcar_ci.sh
```

This uses Garcar's own local runner and does not depend on GitHub-hosted runners. It runs Python compilation, unit tests, loopback HTTP smoke tests, and catalog validation. It stops at the first failure and stores stage logs, a JSON report, and SHA-256 checksums in `platform/.garcar-builds/`. Build subprocesses receive a minimal environment; shell API keys and payment credentials are not forwarded.

A successful local run is evidence for this checkout and device only. It does not deploy the application or approve production use. The direct script `bash run_checks.sh` remains available.


## 10. Verify release evidence (review only)

After the local pipeline passes, copy the build ID printed by the runner and run:

```bash
python release_gate.py .garcar-builds/BUILD_ID/report.json
```

Replace `BUILD_ID` with the exact printed directory name. The gate checks all required stage results, logs, SHA-256 manifest entries, and the no-external-actions declaration. It does not deploy or merge anything. A valid gate result is only permission to begin a human release review.
