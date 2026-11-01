#!/usr/bin/env python3
"""Offline validation for Garcar's division catalog. Python standard library only."""
import json
import sys
from pathlib import Path

EXPECTED = {
    "digital-products", "revenue-automation", "ai-operations-studio",
    "wealth-forge", "enterprise-intelligence", "industry-solutions",
    "infrastructure", "governance-security",
}
FORBIDDEN_AUTHORIZATION = (
    "paid_services_activation_authorized",
    "live_payment_activation_authorized",
    "outbound_email_authorized",
    "production_deployment_authorized",
    "customer_data_access_authorized",
)

def validate(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Invalid JSON: {exc}"]
    divisions = data.get("divisions")
    if not isinstance(divisions, list):
        return ["divisions must be an array"]
    ids = [d.get("id") for d in divisions if isinstance(d, dict)]
    if set(ids) != EXPECTED:
        errors.append(f"Expected exactly 8 division IDs; got {sorted(set(ids))}")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate division IDs")
    offer_ids = []
    for division in divisions:
        if not isinstance(division, dict):
            errors.append("Division entries must be objects")
            continue
        if not isinstance(division.get("offers"), list):
            errors.append(f"{division.get('id')}: offers must be an array")
            continue
        for offer in division["offers"]:
            if not isinstance(offer, dict) or not offer.get("id") or not offer.get("name"):
                errors.append(f"{division.get('id')}: offer needs id and name")
                continue
            offer_ids.append(offer["id"])
            price = offer.get("price")
            if price is not None and (not isinstance(price, (int, float)) or price < 0):
                errors.append(f"{offer['id']}: price must be non-negative number or null")
    if len(offer_ids) != len(set(offer_ids)):
        errors.append("Duplicate offer IDs")
    constraints = data.get("constraints", {})
    for key in FORBIDDEN_AUTHORIZATION:
        if constraints.get(key) is not False:
            errors.append(f"Safety constraint {key} must remain false")
    if not data.get("status"):
        errors.append("Catalog status is required")
    return errors

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("catalog.json")
    problems = validate(target)
    if problems:
        print("CATALOG VALIDATION FAILED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("CATALOG VALIDATION PASSED")
