import os, requests, time
from datetime import datetime
RHNS_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "http://localhost:8000")
NEXUS_WEBHOOK = os.getenv("NEXUS_WEBHOOK_URL")

def run_hourly_check():
    timestamp = datetime.utcnow().isoformat() + "Z"
    try:
        response = requests.get(f"{RHNS_URL}/health", timeout=10)
        is_healthy = response.status_code == 200
        status_msg = "healthy" if is_healthy else f"degraded ({response.status_code})"
    except Exception as e:
        is_healthy = False
        status_msg = f"failed_to_connect: {str(e)}"

    payload = {
        "system": "RHNS Core Monitor",
        "event": "hourly_health_check",
        "status": status_msg,
        "timestamp": timestamp,
        "is_healthy": is_healthy
    }

    if NEXUS_WEBHOOK:
        try:
            requests.post(NEXUS_WEBHOOK, json=payload, timeout=5)
            print(f"[{timestamp}] Logged to NEXUS.")
        except: pass
    else:
        print(f"[{timestamp}] Status: {status_msg}. (NEXUS_WEBHOOK not configured)")

if __name__ == "__main__":
    run_hourly_check()
