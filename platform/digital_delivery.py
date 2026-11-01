"""Test-mode digital checkout, entitlement, and protected-download sandbox.

This module deliberately contains NO Stripe SDK, live payment endpoint, email sender,
or production payment adapter. Synthetic payment events are HMAC-signed locally.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from server import ApiError, append_audit, canonical, clean_text, connect, now_iso

DIGITAL_CATALOG = Path(__file__).resolve().parent.parent / "digital-products" / "catalog.json"
ASSET_FILES = {
    "IA-001": "01_Third_Eye_Science_and_Spirituality.pdf",
    "WA-001": "02_The_Abundance_Blueprint.pdf",
    "MP-001": "03_The_Mind_Reprogramming_Method.pdf",
    "HC-001": "04_The_Connection_Blueprint.pdf",
    "IA-002": "05_The_30_Second_Mindful_Reset.pdf",
    "IA-003": "06_The_Consciousness_Workbook.pdf",
    "WA-002": "07_The_Money_Mindset_Reset.pdf",
    "WA-003": "08_The_Personal_Wealth_Operating_Manual.pdf",
    "MP-002": "09_The_Focus_Protocol.pdf",
    "MP-003": "10_The_30_Day_Mental_Performance_Workbook.pdf",
    "HC-002": "11_The_Relationship_Intelligence_Workbook.pdf",
    "HC-003": "12_The_Communication_Mastery_Guide.pdf",
}
CURRENCY = "usd"
DOWNLOAD_MINUTES = 30
MAX_DOWNLOADS = 3


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def init_digital_schema(db_path: Path | str) -> None:
    with connect(db_path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS digital_orders(
          order_id TEXT PRIMARY KEY,
          product_id TEXT NOT NULL,
          product_title TEXT NOT NULL,
          buyer_ref TEXT NOT NULL,
          amount_cents INTEGER NOT NULL,
          currency TEXT NOT NULL,
          status TEXT NOT NULL,
          mode TEXT NOT NULL CHECK(mode='test'),
          provider_reference TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS digital_events(
          event_id TEXT PRIMARY KEY,
          order_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          payload_sha256 TEXT NOT NULL,
          processed_at TEXT NOT NULL,
          result TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS digital_entitlements(
          entitlement_id TEXT PRIMARY KEY,
          order_id TEXT NOT NULL UNIQUE REFERENCES digital_orders(order_id) ON DELETE RESTRICT,
          product_id TEXT NOT NULL,
          buyer_ref TEXT NOT NULL,
          status TEXT NOT NULL,
          granted_at TEXT NOT NULL,
          revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS digital_download_tokens(
          token_hash TEXT PRIMARY KEY,
          entitlement_id TEXT NOT NULL REFERENCES digital_entitlements(entitlement_id) ON DELETE RESTRICT,
          expires_at TEXT NOT NULL,
          max_downloads INTEGER NOT NULL,
          download_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          revoked_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_digital_orders_status ON digital_orders(status);
        CREATE INDEX IF NOT EXISTS idx_digital_events_order ON digital_events(order_id);
        CREATE INDEX IF NOT EXISTS idx_digital_entitlements_status ON digital_entitlements(status);
        """)


def _catalog(db_path: Path | str) -> dict[str, dict[str, Any]]:
    if not DIGITAL_CATALOG.is_file():
        raise ApiError(503, "Digital product catalog is unavailable.")
    try:
        data = json.loads(DIGITAL_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiError(503, "Digital product catalog could not be read.") from exc
    products = data.get("products")
    if not isinstance(products, list) or len(products) != 12:
        raise ApiError(503, "Digital product catalog integrity check failed.")
    result: dict[str, dict[str, Any]] = {}
    for item in products:
        if not isinstance(item, dict):
            raise ApiError(503, "Digital product catalog contains an invalid entry.")
        pid = item.get("id")
        title = item.get("title")
        price = item.get("price")
        if not isinstance(pid, str) or pid not in ASSET_FILES or not isinstance(title, str):
            raise ApiError(503, "Digital catalog product ID or title is invalid.")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            raise ApiError(503, "Digital catalog price is invalid.")
        result[pid] = {
            "id": pid,
            "title": title,
            "amount_cents": int(round(float(price) * 100)),
            "currency": CURRENCY,
            "status": str(item.get("status", "")),
        }
    if set(result) != set(ASSET_FILES):
        raise ApiError(503, "Digital product ID manifest does not match the catalog.")
    return result


def _state_dir(db_path: Path | str) -> Path:
    override = os.environ.get("GARCAR_PRIVATE_STATE_DIR")
    directory = Path(override) if override else Path(db_path).resolve().parent / "private_state"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    return directory


def _secret(env_name: str, filename: str, db_path: Path | str) -> bytes:
    configured = os.environ.get(env_name)
    if configured:
        raw = configured.encode("utf-8")
        if len(raw) < 32:
            raise ApiError(503, env_name + " must contain at least 32 characters.")
        return raw
    path = _state_dir(db_path) / filename
    if path.exists():
        raw = path.read_bytes()
        if len(raw) < 32:
            raise ApiError(503, "Local digital service secret file is invalid.")
        return raw
    raw = secrets.token_bytes(48)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return raw


def _webhook_secret(db_path: Path | str) -> bytes:
    return _secret("GARCAR_DIGITAL_TEST_WEBHOOK_SECRET", "digital-test-webhook.key", db_path)


def _download_secret(db_path: Path | str) -> bytes:
    return _secret("GARCAR_DIGITAL_DOWNLOAD_SECRET", "digital-download-token.key", db_path)


def _token_hash(token: str, secret: bytes) -> str:
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def _asset_dir(db_path: Path | str) -> Path:
    override = os.environ.get("GARCAR_DIGITAL_ASSET_DIR")
    return Path(override) if override else Path(db_path).resolve().parent / "private_assets"


def _resolve_asset(product_id: str, db_path: Path | str) -> Path:
    filename = ASSET_FILES.get(product_id)
    if not filename:
        raise ApiError(404, "Digital product asset is not configured.")
    directory = _asset_dir(db_path).resolve()
    candidate = (directory / filename).resolve()
    if candidate.parent != directory:
        raise ApiError(400, "Invalid digital asset path.")
    if not candidate.is_file():
        raise ApiError(503, "Paid asset is not installed in the private asset directory.")
    if candidate.suffix.lower() != ".pdf":
        raise ApiError(415, "Only approved PDF assets are supported.")
    return candidate


def create_test_checkout(data: dict[str, Any], db_path: Path | str) -> dict[str, Any]:
    init_digital_schema(db_path)
    product_id = clean_text(data.get("product_id"), "product_id", 20, True)
    products = _catalog(db_path)
    product = products.get(product_id)
    if not product:
        raise ApiError(404, "Digital product not found.")
    # Preview status is not a live offer. This creates a synthetic order only.
    order_id = "test_order_" + uuid.uuid4().hex
    provider_reference = "test_checkout_" + uuid.uuid4().hex
    buyer_ref = "test_buyer_" + uuid.uuid4().hex
    stamp = now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO digital_orders
          (order_id,product_id,product_title,buyer_ref,amount_cents,currency,status,mode,
           provider_reference,created_at,updated_at)
          VALUES(?,?,?,?,?,?,'pending','test',?,?,?)""",
          (order_id, product_id, product["title"], buyer_ref, product["amount_cents"],
           CURRENCY, provider_reference, stamp, stamp))
        append_audit(db, "digital.test_order.created", "digital_order", order_id,
                     {"product_id": product_id, "amount_cents": product["amount_cents"], "mode": "test"})
    return {
        "order_id": order_id,
        "product_id": product_id,
        "product_title": product["title"],
        "amount_cents": product["amount_cents"],
        "currency": CURRENCY,
        "status": "pending",
        "mode": "test",
        "buyer_ref": buyer_ref,
        "payment_link_created": False,
        "payment_taken": False,
        "note": "Synthetic test order only. No real checkout, payment, email, or customer record was created.",
    }


def _signed_body(payload: dict[str, Any], db_path: Path | str) -> tuple[bytes, str]:
    raw = canonical(payload).encode("utf-8")
    signature = hmac.new(_webhook_secret(db_path), raw, hashlib.sha256).hexdigest()
    return raw, "sha256=" + signature


def process_test_webhook(raw_body: bytes, signature: str, db_path: Path | str) -> dict[str, Any]:
    init_digital_schema(db_path)
    expected_prefix = "sha256="
    if not isinstance(signature, str) or not signature.startswith(expected_prefix):
        raise ApiError(401, "Missing or malformed test webhook signature.")
    expected = hmac.new(_webhook_secret(db_path), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature[len(expected_prefix):]):
        raise ApiError(401, "Test webhook signature is invalid.")
    if len(raw_body) > 32768:
        raise ApiError(413, "Test webhook body exceeds 32 KiB.")
    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError(400, "Test webhook body is not valid JSON.") from exc
    if not isinstance(event, dict):
        raise ApiError(400, "Test webhook must be a JSON object.")
    if event.get("mode") != "test" or event.get("livemode") is not False:
        raise ApiError(403, "Only explicit test-mode events are accepted.")
    event_id = clean_text(event.get("id"), "event.id", 100, True)
    if not event_id.startswith("evt_test_"):
        raise ApiError(403, "Only synthetic test event IDs are accepted.")
    event_type = clean_text(event.get("type"), "event.type", 50, True)
    if event_type not in {"payment_succeeded", "payment_refunded"}:
        raise ApiError(400, "Unsupported synthetic payment event.")
    order_id = clean_text(event.get("order_id"), "order_id", 100, True)
    provider_ref = clean_text(event.get("payment_reference"), "payment_reference", 120, True)
    checkout_ref = clean_text(event.get("checkout_reference"), "checkout_reference", 120, True)
    if not provider_ref.startswith("test_payment_"):
        raise ApiError(403, "Only synthetic test payment references are accepted.")
    product_id = clean_text(event.get("product_id"), "product_id", 20, True)
    amount = event.get("amount_cents")
    currency = clean_text(event.get("currency"), "currency", 3, True).lower()
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ApiError(400, "amount_cents must be a positive integer.")
    if currency != CURRENCY:
        raise ApiError(400, "Digital test orders must use USD.")
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    download_token: str | None = None
    result: dict[str, Any]
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM digital_events WHERE event_id=?", (event_id,)).fetchone():
            return {"accepted": True, "duplicate": True, "event_id": event_id,
                    "entitlement_created": False, "download_token": None}
        order = db.execute("SELECT * FROM digital_orders WHERE order_id=?", (order_id,)).fetchone()
        if not order:
            raise ApiError(404, "Synthetic order does not exist.")
        catalog_product = _catalog(db_path).get(product_id)
        if not catalog_product or order["product_id"] != product_id:
            raise ApiError(400, "Product ID does not match the original order.")
        if order["mode"] != "test" or checkout_ref != order["provider_reference"]:
            raise ApiError(403, "Order is not a test-mode order.")
        if amount != order["amount_cents"] or amount != catalog_product["amount_cents"]:
            raise ApiError(409, "Payment amount does not match the authoritative catalog price.")
        if event_type == "payment_succeeded":
            if order["status"] != "pending":
                if order["status"] == "paid":
                    raise ApiError(409, "Order is already paid.")
                raise ApiError(409, "Order is not eligible for payment.")
            stamp = now_iso()
            db.execute("UPDATE digital_orders SET status='paid',updated_at=? WHERE order_id=?", (stamp, order_id))
            entitlement_id = "ent_" + uuid.uuid4().hex
            db.execute("""INSERT INTO digital_entitlements
              (entitlement_id,order_id,product_id,buyer_ref,status,granted_at,revoked_at)
              VALUES(?,?,?,?, 'active', ?, NULL)""",
              (entitlement_id, order_id, product_id, order["buyer_ref"], stamp))
            raw_token = secrets.token_urlsafe(40)
            secret = _download_secret(db_path)
            expiry = (_utc() + timedelta(minutes=DOWNLOAD_MINUTES)).isoformat(timespec="seconds")
            db.execute("""INSERT INTO digital_download_tokens
              (token_hash,entitlement_id,expires_at,max_downloads,download_count,created_at,revoked_at)
              VALUES(?,?,?, ?,0,?,NULL)""",
              (_token_hash(raw_token, secret), entitlement_id, expiry, MAX_DOWNLOADS, stamp))
            download_token = raw_token
            append_audit(db, "digital.test_payment.succeeded", "digital_order", order_id,
                         {"event_id": event_id, "product_id": product_id, "amount_cents": amount,
                          "entitlement_id": entitlement_id, "mode": "test"})
            result = {"accepted": True, "duplicate": False, "event_id": event_id,
                      "order_id": order_id, "order_status": "paid",
                      "entitlement_id": entitlement_id, "entitlement_created": True,
                      "download_expires_at": expiry, "download_limit": MAX_DOWNLOADS,
                      "download_token": download_token, "download_path": "/digital/download/" + download_token, "mode": "test",
                      "note": "Synthetic payment only. No real money was collected."}
        else:
            if order["status"] != "paid":
                raise ApiError(409, "Only a paid synthetic order can be refunded.")
            stamp = now_iso()
            db.execute("UPDATE digital_orders SET status='refunded',updated_at=? WHERE order_id=?", (stamp, order_id))
            db.execute("UPDATE digital_entitlements SET status='revoked',revoked_at=? WHERE order_id=?",
                       (stamp, order_id))
            db.execute("""UPDATE digital_download_tokens SET revoked_at=?
              WHERE entitlement_id IN (SELECT entitlement_id FROM digital_entitlements WHERE order_id=?)""",
              (stamp, order_id))
            append_audit(db, "digital.test_payment.refunded", "digital_order", order_id,
                         {"event_id": event_id, "product_id": product_id, "amount_cents": amount, "mode": "test"})
            result = {"accepted": True, "duplicate": False, "event_id": event_id,
                      "order_id": order_id, "order_status": "refunded",
                      "entitlement_created": False, "entitlement_revoked": True,
                      "mode": "test", "note": "Synthetic refund only. No real money was moved."}
        db.execute("""INSERT INTO digital_events(event_id,order_id,event_type,payload_sha256,processed_at,result)
          VALUES(?,?,?,?,?,?)""",
          (event_id, order_id, event_type, payload_hash, now_iso(), "accepted"))
    return result


def simulate_test_payment(order_id: str, db_path: Path | str) -> dict[str, Any]:
    init_digital_schema(db_path)
    with connect(db_path) as db:
        order = db.execute("SELECT * FROM digital_orders WHERE order_id=?", (order_id,)).fetchone()
    if not order:
        raise ApiError(404, "Synthetic order not found.")
    event = {
        "id": "evt_test_" + uuid.uuid4().hex,
        "type": "payment_succeeded",
        "mode": "test",
        "livemode": False,
        "order_id": order["order_id"],
        "product_id": order["product_id"],
        "amount_cents": order["amount_cents"],
        "currency": order["currency"],
        "payment_reference": "test_payment_" + uuid.uuid4().hex,
        "checkout_reference": order["provider_reference"],
    }
    raw, signature = _signed_body(event, db_path)
    return process_test_webhook(raw, signature, db_path)


def simulate_test_refund(order_id: str, db_path: Path | str) -> dict[str, Any]:
    init_digital_schema(db_path)
    with connect(db_path) as db:
        order = db.execute("SELECT * FROM digital_orders WHERE order_id=?", (order_id,)).fetchone()
    if not order:
        raise ApiError(404, "Synthetic order not found.")
    event = {
        "id": "evt_test_" + uuid.uuid4().hex,
        "type": "payment_refunded",
        "mode": "test",
        "livemode": False,
        "order_id": order["order_id"],
        "product_id": order["product_id"],
        "amount_cents": order["amount_cents"],
        "currency": order["currency"],
        "payment_reference": "test_payment_" + uuid.uuid4().hex,
    }
    raw, signature = _signed_body(event, db_path)
    return process_test_webhook(raw, signature, db_path)


def consume_download_token(token: str, db_path: Path | str) -> tuple[Path, dict[str, Any]]:
    init_digital_schema(db_path)
    token = clean_text(token, "download_token", 200, True)
    secret = _download_secret(db_path)
    digest = _token_hash(token, secret)
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("""SELECT t.*,e.status AS entitlement_status,e.product_id,e.order_id,o.status AS order_status
          FROM digital_download_tokens t
          JOIN digital_entitlements e ON e.entitlement_id=t.entitlement_id
          JOIN digital_orders o ON o.order_id=e.order_id
          WHERE t.token_hash=?""", (digest,)).fetchone()
        if not row:
            raise ApiError(404, "Download token is invalid.")
        if row["revoked_at"] or row["entitlement_status"] != "active" or row["order_status"] != "paid":
            raise ApiError(403, "Download entitlement is no longer active.")
        if datetime.fromisoformat(row["expires_at"]) <= _utc():
            raise ApiError(410, "Download token has expired.")
        if row["download_count"] >= row["max_downloads"]:
            raise ApiError(429, "Download limit reached.")
        path = _resolve_asset(row["product_id"], db_path)
        db.execute("UPDATE digital_download_tokens SET download_count=download_count+1 WHERE token_hash=?", (digest,))
        db.execute("UPDATE digital_orders SET updated_at=? WHERE order_id=?", (now_iso(), row["order_id"]))
        append_audit(db, "digital.download.accessed", "digital_order", row["order_id"],
                     {"product_id": row["product_id"], "remaining_uses": row["max_downloads"] - row["download_count"] - 1})
        meta = {"product_id": row["product_id"], "order_id": row["order_id"],
                "remaining_downloads": row["max_downloads"] - row["download_count"] - 1}
    return path, meta


def list_digital_orders(db_path: Path | str) -> list[dict[str, Any]]:
    init_digital_schema(db_path)
    with connect(db_path) as db:
        rows = db.execute("""SELECT order_id,product_id,product_title,buyer_ref,amount_cents,currency,
          status,mode,provider_reference,created_at,updated_at
          FROM digital_orders ORDER BY created_at DESC LIMIT 200""").fetchall()
    return [dict(row) for row in rows]


def list_digital_entitlements(db_path: Path | str) -> list[dict[str, Any]]:
    init_digital_schema(db_path)
    with connect(db_path) as db:
        rows = db.execute("""SELECT e.entitlement_id,e.order_id,e.product_id,e.buyer_ref,e.status,
          e.granted_at,e.revoked_at,o.status AS order_status
          FROM digital_entitlements e JOIN digital_orders o ON o.order_id=e.order_id
          ORDER BY e.granted_at DESC LIMIT 200""").fetchall()
    return [dict(row) for row in rows]


def digital_delivery_health(db_path: Path | str) -> dict[str, Any]:
    init_digital_schema(db_path)
    products = _catalog(db_path)
    directory = _asset_dir(db_path)
    asset_state = {pid: (directory / ASSET_FILES[pid]).is_file() for pid in sorted(products)}
    return {
        "mode": "test_only",
        "live_payments_enabled": False,
        "payment_provider_connected": False,
        "checkout_sessions_created": False,
        "products": len(products),
        "assets_directory": str(directory),
        "assets_installed": sum(asset_state.values()),
        "assets_missing": [pid for pid, exists in asset_state.items() if not exists],
        "download_expiry_minutes": DOWNLOAD_MINUTES,
        "max_downloads": MAX_DOWNLOADS,
        "note": "A local synthetic payment is not a real payment. This service is not a production payment integration.",
    }
