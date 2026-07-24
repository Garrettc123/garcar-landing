import os, requests
from pydantic import BaseModel
from datetime import datetime

class ThreatReport(BaseModel):
    severity: str
    source_ip: str
    description: str
    action_taken: str

NEXUS_WEBHOOK = os.getenv("NEXUS_WEBHOOK_URL")

def bind_cti_event(threat: ThreatReport):
    timestamp = datetime.utcnow().isoformat() + "Z"
    payload = {
        "system": "Defender OS Phase 5 CTI Agent",
        "event": "threat_detected",
        "status": "mitigated" if threat.action_taken == "block" else "escalated",
        "details": threat.model_dump(),
        "timestamp": timestamp,
        "action_required": threat.severity == "critical"
    }
    if NEXUS_WEBHOOK:
        requests.post(NEXUS_WEBHOOK, json=payload)
