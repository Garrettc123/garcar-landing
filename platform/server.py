#!/usr/bin/env python3
"""Garcar Enterprise local-first operating console. Python standard library only."""
from __future__ import annotations
import argparse, hashlib, hmac, json, os, re, secrets, sqlite3, sys, uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
CATALOG_PATH=ROOT/"divisions"/"catalog.json"
DB_PATH=Path(os.environ.get("GARCAR_DB_PATH",HERE/"garcar.local.sqlite3"))
STATUSES={"new","reviewed","qualified","proposal","contract","closed_won","closed_lost"}
STAGES={"target","researched","discovery","qualified","proposal","contract","paid_pending_verification","delivered","lost"}
APPROVAL_ACTIONS={"email.send","sms.send","payment.create","refund.issue","production.deploy","customer_data.export","secret.rotate","infrastructure.change","external_api.write"}
DIVISION_IDS={"digital-products","revenue-automation","ai-operations-studio","wealth-forge","enterprise-intelligence","industry-solutions","infrastructure","governance-security"}

class ApiError(Exception):
    def __init__(self,status:int,message:str):
        super().__init__(message); self.status=status; self.message=message

def now_iso()->str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect(db_path:Path|str=DB_PATH)->sqlite3.Connection:
    path=Path(db_path); path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10); db.row_factory=sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA foreign_keys=ON"); db.execute("PRAGMA busy_timeout=10000")
    return db

def init_db(db_path:Path|str=DB_PATH)->None:
    with connect(db_path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS leads(
          id TEXT PRIMARY KEY, company TEXT NOT NULL, category TEXT NOT NULL, source TEXT NOT NULL,
          service_need TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'new', owner TEXT NOT NULL DEFAULT '',
          estimated_value_cents INTEGER NOT NULL DEFAULT 0, next_step TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS opportunities(
          id TEXT PRIMARY KEY, lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE RESTRICT,
          offer_id TEXT NOT NULL, amount_cents INTEGER NOT NULL, stage TEXT NOT NULL,
          next_step TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS validation_interviews(
          id TEXT PRIMARY KEY, market TEXT NOT NULL, product_id TEXT NOT NULL DEFAULT '', interview_date TEXT NOT NULL,
          source TEXT NOT NULL, follow_up_permission INTEGER NOT NULL DEFAULT 0, need_summary TEXT NOT NULL DEFAULT '',
          objection TEXT NOT NULL DEFAULT '', price_reaction TEXT NOT NULL DEFAULT '', next_action TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS approvals(
          id TEXT PRIMARY KEY, action_type TEXT NOT NULL, resource TEXT NOT NULL, scope TEXT NOT NULL,
          requested_by TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          decision_comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, decided_at TEXT);
        CREATE TABLE IF NOT EXISTS audit_events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, event_type TEXT NOT NULL,
          entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, actor TEXT NOT NULL, payload_json TEXT NOT NULL,
          occurred_at TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage);
        CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
        CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type,entity_id);

        CREATE TABLE IF NOT EXISTS finance_entries(
          id TEXT PRIMARY KEY, entry_type TEXT NOT NULL, label TEXT NOT NULL, category TEXT NOT NULL,
          amount_cents INTEGER NOT NULL, happened_on TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'manual',
          notes TEXT NOT NULL DEFAULT '', revenue_class TEXT NOT NULL DEFAULT 'unknown',
          collection_state TEXT NOT NULL DEFAULT 'unknown', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS knowledge_docs(
          id TEXT PRIMARY KEY, title TEXT NOT NULL, division_id TEXT NOT NULL, source_ref TEXT NOT NULL,
          content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS work_items(
          id TEXT PRIMARY KEY, division_id TEXT NOT NULL, workflow_type TEXT NOT NULL, title TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'normal', status TEXT NOT NULL DEFAULT 'open',
          due_date TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_finance_date ON finance_entries(happened_on);
        CREATE INDEX IF NOT EXISTS idx_knowledge_division ON knowledge_docs(division_id);
        CREATE TABLE IF NOT EXISTS knowledge_links(
          id TEXT PRIMARY KEY, from_doc_id TEXT NOT NULL REFERENCES knowledge_docs(id) ON DELETE RESTRICT,
          to_doc_id TEXT NOT NULL REFERENCES knowledge_docs(id) ON DELETE RESTRICT,
          relation TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(from_doc_id,to_doc_id,relation));
        CREATE INDEX IF NOT EXISTS idx_knowledge_links_from ON knowledge_links(from_doc_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_links_to ON knowledge_links(to_doc_id);

        CREATE INDEX IF NOT EXISTS idx_work_status ON work_items(status);
        CREATE TABLE IF NOT EXISTS product_readiness(
          offer_id TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'specified',
          evidence_ref TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_product_readiness_state ON product_readiness(state);
        CREATE TABLE IF NOT EXISTS workflow_definitions(
          workflow_key TEXT PRIMARY KEY, title TEXT NOT NULL, division_id TEXT NOT NULL,
          description TEXT NOT NULL, steps_json TEXT NOT NULL, version TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS workflow_runs(
          id TEXT PRIMARY KEY, workflow_key TEXT NOT NULL REFERENCES workflow_definitions(workflow_key) ON DELETE RESTRICT,
          status TEXT NOT NULL DEFAULT 'active', current_step_index INTEGER NOT NULL DEFAULT 0,
          context_json TEXT NOT NULL DEFAULT '{}', notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);

        finance_columns = {row["name"] for row in db.execute("PRAGMA table_info(finance_entries)")}
        if "revenue_class" not in finance_columns:
            db.execute("ALTER TABLE finance_entries ADD COLUMN revenue_class TEXT NOT NULL DEFAULT 'unknown'")
        if "collection_state" not in finance_columns:
            db.execute("ALTER TABLE finance_entries ADD COLUMN collection_state TEXT NOT NULL DEFAULT 'unknown'")

        """)

def canonical(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def append_audit(db:sqlite3.Connection,event_type:str,entity_type:str,entity_id:str,payload:dict[str,Any],actor:str="local-owner")->str:
    last=db.execute("SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
    previous=last["event_hash"] if last else "GENESIS"
    event_id=str(uuid.uuid4()); occurred=now_iso(); payload_json=canonical(payload)
    material=canonical({"event_id":event_id,"event_type":event_type,"entity_type":entity_type,"entity_id":entity_id,
      "actor":actor,"payload_json":payload_json,"occurred_at":occurred,"previous_hash":previous})
    digest=hashlib.sha256(material.encode()).hexdigest()
    db.execute("""INSERT INTO audit_events(event_id,event_type,entity_type,entity_id,actor,payload_json,occurred_at,previous_hash,event_hash)
      VALUES(?,?,?,?,?,?,?,?,?)""",(event_id,event_type,entity_type,entity_id,actor,payload_json,occurred,previous,digest))
    return digest

def verify_ledger(db_path:Path|str=DB_PATH)->dict[str,Any]:
    with connect(db_path) as db: rows=db.execute("SELECT * FROM audit_events ORDER BY seq").fetchall()
    previous="GENESIS"
    for row in rows:
        if row["previous_hash"]!=previous:
            return {"valid":False,"events":len(rows),"failed_seq":row["seq"],"reason":"previous_hash_mismatch"}
        material=canonical({"event_id":row["event_id"],"event_type":row["event_type"],"entity_type":row["entity_type"],
          "entity_id":row["entity_id"],"actor":row["actor"],"payload_json":row["payload_json"],
          "occurred_at":row["occurred_at"],"previous_hash":row["previous_hash"]})
        expected=hashlib.sha256(material.encode()).hexdigest()
        if not hmac.compare_digest(expected,row["event_hash"]):
            return {"valid":False,"events":len(rows),"failed_seq":row["seq"],"reason":"event_hash_mismatch"}
        previous=row["event_hash"]
    return {"valid":True,"events":len(rows),"head_hash":previous}

def load_catalog()->dict[str,Any]:
    if not CATALOG_PATH.exists(): raise ApiError(503,"divisions/catalog.json was not found.")
    try: data=json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ApiError(503,"Catalog could not be read.") from exc
    ids={d.get("id") for d in data.get("divisions",[]) if isinstance(d,dict)}
    if ids!=DIVISION_IDS: raise ApiError(503,"Catalog division integrity check failed.")
    return data

def offer_index()->dict[str,dict[str,Any]]:
    c=load_catalog()
    return {o["id"]:{**o,"division_id":d["id"],"division_name":d["name"]} for d in c["divisions"] for o in d.get("offers",[])}

def clean_text(value:Any,field:str,maximum:int=500,required:bool=False)->str:
    if value is None: value=""
    if not isinstance(value,str): raise ApiError(400,field+" must be text.")
    value=value.strip()
    if required and not value: raise ApiError(400,field+" is required.")
    if len(value)>maximum: raise ApiError(400,field+" is too long.")
    return value

def create_lead(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    company=clean_text(data.get("company"),"company",140,True)
    category=clean_text(data.get("category"),"category",60,True)
    source=clean_text(data.get("source"),"source",60,True)
    service=clean_text(data.get("service_need"),"service_need",240)
    owner=clean_text(data.get("owner"),"owner",100)
    next_step=clean_text(data.get("next_step"),"next_step",240)
    notes=clean_text(data.get("notes"),"notes",1000)
    value=data.get("estimated_value_cents",0)
    if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=10_000_000_000: raise ApiError(400,"estimated_value_cents must be a non-negative integer.")
    rid=str(uuid.uuid4()); stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO leads(id,company,category,source,service_need,status,owner,estimated_value_cents,next_step,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,'new',?,?,?,?,?,?)""",(rid,company,category,source,service,owner,value,next_step,notes,stamp,stamp))
        append_audit(db,"lead.created","lead",rid,{"company":company,"category":category,"source":source})
        row=dict(db.execute("SELECT * FROM leads WHERE id=?",(rid,)).fetchone())
    return row

def update_lead(rid:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    if not data or set(data)-{"status","owner","next_step","notes"}: raise ApiError(400,"Only status, owner, next_step, notes may change.")
    updates={}
    if "status" in data:
        s=clean_text(data["status"],"status",30,True)
        if s not in STATUSES: raise ApiError(400,"Invalid lead status.")
        updates["status"]=s
    for f,n in (("owner",100),("next_step",240),("notes",1000)):
        if f in data: updates[f]=clean_text(data[f],f,n)
    updates["updated_at"]=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM leads WHERE id=?",(rid,)).fetchone(): raise ApiError(404,"Lead not found.")
        db.execute("UPDATE leads SET "+",".join(f+"=?" for f in updates)+" WHERE id=?",(*updates.values(),rid))
        append_audit(db,"lead.updated","lead",rid,updates)
        result=dict(db.execute("SELECT * FROM leads WHERE id=?",(rid,)).fetchone())
    return result

def create_opportunity(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    lead=clean_text(data.get("lead_id"),"lead_id",64,True); offer=clean_text(data.get("offer_id"),"offer_id",32,True)
    if offer not in offer_index(): raise ApiError(400,"Unknown offer_id.")
    amount=data.get("amount_cents")
    if isinstance(amount,bool) or not isinstance(amount,int) or not 0<amount<=10_000_000_000: raise ApiError(400,"amount_cents must be a positive integer.")
    stage=clean_text(data.get("stage","target"),"stage",40,True)
    if stage not in STAGES: raise ApiError(400,"Invalid opportunity stage.")
    next_step=clean_text(data.get("next_step"),"next_step",240); notes=clean_text(data.get("notes"),"notes",1000)
    rid=str(uuid.uuid4()); stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM leads WHERE id=?",(lead,)).fetchone(): raise ApiError(404,"Lead not found.")
        db.execute("""INSERT INTO opportunities(id,lead_id,offer_id,amount_cents,stage,next_step,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?)""",(rid,lead,offer,amount,stage,next_step,notes,stamp,stamp))
        append_audit(db,"opportunity.created","opportunity",rid,{"lead_id":lead,"offer_id":offer,"amount_cents":amount,"stage":stage})
        result=dict(db.execute("SELECT * FROM opportunities WHERE id=?",(rid,)).fetchone())
    return result

def update_opportunity(rid:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    if not data or set(data)-{"stage","next_step","notes"}: raise ApiError(400,"Only stage, next_step, notes may change.")
    updates={}
    if "stage" in data:
        stage=clean_text(data["stage"],"stage",40,True)
        if stage not in STAGES: raise ApiError(400,"Invalid opportunity stage.")
        updates["stage"]=stage
    for f,n in (("next_step",240),("notes",1000)):
        if f in data: updates[f]=clean_text(data[f],f,n)
    updates["updated_at"]=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM opportunities WHERE id=?",(rid,)).fetchone(): raise ApiError(404,"Opportunity not found.")
        db.execute("UPDATE opportunities SET "+",".join(f+"=?" for f in updates)+" WHERE id=?",(*updates.values(),rid))
        append_audit(db,"opportunity.updated","opportunity",rid,updates)
        result=dict(db.execute("SELECT * FROM opportunities WHERE id=?",(rid,)).fetchone())
    return result

def create_interview(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    market=clean_text(data.get("market"),"market",80,True); product=clean_text(data.get("product_id"),"product_id",32)
    if product and product not in offer_index(): raise ApiError(400,"Unknown product_id.")
    source=clean_text(data.get("source"),"source",140,True); date=clean_text(data.get("interview_date") or now_iso()[:10],"interview_date",20,True)
    permission=data.get("follow_up_permission",False)
    if not isinstance(permission,bool): raise ApiError(400,"follow_up_permission must be boolean.")
    fields={k:clean_text(data.get(k),k,n) for k,n in (("need_summary",500),("objection",300),("price_reaction",200),("next_action",200))}
    rid=str(uuid.uuid4()); stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO validation_interviews(id,market,product_id,interview_date,source,follow_up_permission,need_summary,objection,price_reaction,next_action,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(rid,market,product,date,source,int(permission),fields["need_summary"],fields["objection"],fields["price_reaction"],fields["next_action"],stamp))
        append_audit(db,"interview.recorded","interview",rid,{"market":market,"product_id":product,"follow_up_permission":permission})
        result=dict(db.execute("SELECT * FROM validation_interviews WHERE id=?",(rid,)).fetchone())
    return result

def create_approval(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    action=clean_text(data.get("action_type"),"action_type",60,True)
    if action not in APPROVAL_ACTIONS: raise ApiError(400,"Unknown action_type.")
    resource=clean_text(data.get("resource"),"resource",180,True); scope=clean_text(data.get("scope"),"scope",500,True)
    actor=clean_text(data.get("requested_by","local-owner"),"requested_by",100,True)
    minutes=data.get("expires_minutes",60)
    if isinstance(minutes,bool) or not isinstance(minutes,int) or not 1<=minutes<=1440: raise ApiError(400,"expires_minutes must be 1–1440.")
    rid=str(uuid.uuid4()); stamp=now_iso(); expires=(datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat(timespec="seconds")
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO approvals(id,action_type,resource,scope,requested_by,expires_at,status,created_at)
          VALUES(?,?,?,?,?,?,'pending',?)""",(rid,action,resource,scope,actor,expires,stamp))
        append_audit(db,"approval.requested","approval",rid,{"action_type":action,"resource":resource,"expires_at":expires})
        result=dict(db.execute("SELECT * FROM approvals WHERE id=?",(rid,)).fetchone())
    return result

def decide_approval(rid:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    decision=clean_text(data.get("decision"),"decision",20,True)
    if decision not in {"approved","rejected"}: raise ApiError(400,"decision must be approved or rejected.")
    comment=clean_text(data.get("comment"),"comment",500)
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT * FROM approvals WHERE id=?",(rid,)).fetchone()
        if not row: raise ApiError(404,"Approval not found.")
        if row["status"]!="pending": raise ApiError(409,"Approval is not pending.")
        if datetime.fromisoformat(row["expires_at"])<=datetime.now(timezone.utc):
            db.execute("UPDATE approvals SET status='expired',decided_at=? WHERE id=?",(now_iso(),rid))
            append_audit(db,"approval.expired","approval",rid,{"action_type":row["action_type"]})
            result={"id":rid,"status":"expired","execution_performed":False}
        else:
            stamp=now_iso(); db.execute("UPDATE approvals SET status=?,decision_comment=?,decided_at=? WHERE id=?",(decision,comment,stamp,rid))
            append_audit(db,"approval.decided","approval",rid,{"decision":decision,"comment":comment})
            result=dict(db.execute("SELECT * FROM approvals WHERE id=?",(rid,)).fetchone())
            result["execution_performed"]=False
    result["note"]="Decision record only. No external action is executed."
    return result

def simulate_lead_value(data:dict[str,Any])->dict[str,Any]:
    def num(key:str,lo:float,hi:float)->float:
        val=data.get(key)
        if isinstance(val,bool) or not isinstance(val,(int,float)) or not lo<=val<=hi: raise ApiError(400,f"{key} must be between {lo} and {hi}.")
        return float(val)
    inbound=num("inbound_leads",0,100000); missed=num("missed_rate",0,1)
    recovery=num("recovery_of_missed",0,1); booking=num("booking_rate",0,1); avg=num("average_job_value",0,10000000)
    contacted=inbound*missed*recovery; bookings=contacted*booking; gross=bookings*avg
    return {"additional_contacted_leads_scenario":round(contacted,2),"expected_bookings_scenario":round(bookings,2),
      "illustrative_gross_job_value_scenario":round(gross,2),"assumptions":data,
      "disclaimer":"Illustrative scenario only; not a forecast, guarantee, profit calculation, or verified revenue."}

def list_records(table:str,db_path:Path|str=DB_PATH)->list[dict[str,Any]]:
    allowed={"leads","opportunities","approvals","validation_interviews","finance_entries","knowledge_docs","work_items"}
    if table not in allowed: raise ApiError(404,"Unknown collection.")
    with connect(db_path) as db: rows=db.execute("SELECT * FROM "+table+" ORDER BY created_at DESC LIMIT 250").fetchall()
    return [dict(r) for r in rows]

def dashboard(db_path:Path|str=DB_PATH)->dict[str,Any]:
    with connect(db_path) as db:
        leads=db.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]
        lead_counts={r["status"]:r["n"] for r in db.execute("SELECT status,COUNT(*) n FROM leads GROUP BY status")}
        opps=db.execute("SELECT COUNT(*) n FROM opportunities").fetchone()["n"]
        stage_counts={r["stage"]:r["n"] for r in db.execute("SELECT stage,COUNT(*) n FROM opportunities GROUP BY stage")}
        pipeline=db.execute("SELECT COALESCE(SUM(amount_cents),0) n FROM opportunities WHERE stage IN ('proposal','contract','paid_pending_verification')").fetchone()["n"]
        interviews=db.execute("SELECT COUNT(*) n FROM validation_interviews").fetchone()["n"]
        pending=db.execute("SELECT COUNT(*) n FROM approvals WHERE status='pending'").fetchone()["n"]
    return {"leads_total":leads,"lead_counts":lead_counts,"opportunities_total":opps,"stage_counts":stage_counts,
      "pipeline_value_cents_not_revenue":pipeline,"validation_interviews":interviews,"pending_approvals":pending}

def demo_seed(db_path:Path|str=DB_PATH)->int:
    with connect(db_path) as db:
        if db.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]: return 0
    rows=[
      {"company":"DEMO — North Star HVAC","category":"HVAC","source":"synthetic_demo","service_need":"Missed web enquiries","owner":"Demo operator","estimated_value_cents":250000,"next_step":"Review synthetic flow","notes":"Synthetic data only."},
      {"company":"DEMO — Clear Path Roofing","category":"Roofing","source":"synthetic_demo","service_need":"After-hours lead handoff","owner":"Demo operator","estimated_value_cents":500000,"next_step":"Map callback process","notes":"Synthetic data only."}
    ]
    for row in rows:create_lead(row,db_path)
    return len(rows)



RELEASE_STATES={"specified","built_local","tested_local","sandbox_verified","approved_for_production","deployed_and_verified"}

def sync_product_readiness(db_path:Path|str=DB_PATH)->int:
    offers=offer_index();stamp=now_iso();created=0
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        for oid,offer in offers.items():
            initial="built_local" if "preview_created" in str(offer.get("status","")) else "specified"
            evidence="Private preview manuscript bundle; not for sale and not deployed." if initial=="built_local" else ""
            cur=db.execute("INSERT OR IGNORE INTO product_readiness(offer_id,state,evidence_ref,updated_at) VALUES(?,?,?,?)",
                           (oid,initial,evidence,stamp))
            created+=cur.rowcount
    return created

def update_product_readiness(offer_id:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    if offer_id not in offer_index():raise ApiError(404,"Unknown product/offer ID.")
    if not data or set(data)-{"state","evidence_ref","notes"}:raise ApiError(400,"Only state, evidence_ref, and notes may be updated.")
    state=clean_text(data.get("state"),"state",40,True)
    if state not in RELEASE_STATES:raise ApiError(400,"Invalid release state.")
    evidence=clean_text(data.get("evidence_ref"),"evidence_ref",500)
    notes=clean_text(data.get("notes"),"notes",1000)
    if state!="specified" and not evidence:raise ApiError(400,"A reference to evidence is required for states beyond specified.")
    stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT OR IGNORE INTO product_readiness(offer_id,state,updated_at) VALUES(?,'specified',?)",(offer_id,stamp))
        db.execute("UPDATE product_readiness SET state=?,evidence_ref=?,notes=?,updated_at=? WHERE offer_id=?",
                   (state,evidence,notes,stamp,offer_id))
        append_audit(db,"product.readiness.updated","product",offer_id,{"state":state,"evidence_ref":evidence})
        row=dict(db.execute("SELECT * FROM product_readiness WHERE offer_id=?",(offer_id,)).fetchone())
    row["evidence_is_independently_verified"]=False
    return row

def list_product_readiness(db_path:Path|str=DB_PATH)->dict[str,Any]:
    sync_product_readiness(db_path)
    offers=offer_index()
    with connect(db_path) as db:rows=db.execute("SELECT * FROM product_readiness ORDER BY offer_id").fetchall()
    items=[]
    for row in rows:
        item=dict(row);offer=offers.get(item["offer_id"],{})
        item["name"]=offer.get("name","");item["division_id"]=offer.get("division_id","");item["division_name"]=offer.get("division_name","")
        item["catalog_status"]=offer.get("status","");item["price"]=offer.get("price")
        items.append(item)
    counts={state:sum(1 for item in items if item["state"]==state) for state in sorted(RELEASE_STATES)}
    return {"total":len(items),"counts":counts,"items":items,
      "disclaimer":"Release states and evidence references are operator-entered records. They are not independently verified by this local register."}




KNOWLEDGE_RELATIONS={"supports","contradicts","supersedes","related_to"}


WORKFLOW_TEMPLATES=[
 {"workflow_key":"lead_response_v1","title":"Lead Response","division_id":"revenue-automation",
  "description":"Record, qualify, assign, and review a lead without sending messages.",
  "steps":["lead_intake","source_validation","owner_assignment","human_response_record","outcome_record"]},
 {"workflow_key":"document_review_v1","title":"Document Intake Review","division_id":"ai-operations-studio",
  "description":"Extract candidate text fields, require human verification, and record disposition.",
  "steps":["document_received","field_extraction","human_verification","record_complete"]},
 {"workflow_key":"support_reply_v1","title":"Support Reply Review","division_id":"ai-operations-studio",
  "description":"Find approved sources, prepare a draft, require owner review, and record outcome.",
  "steps":["knowledge_lookup","draft_prepared","human_review","response_outcome_record"]},
 {"workflow_key":"dispatch_exception_v1","title":"Dispatch Exception Desk","division_id":"industry-solutions",
  "description":"Record an exception, require dispatcher review, and record a resolution.",
  "steps":["event_recorded","dispatcher_review","resolution_recorded","closed"]},
 {"workflow_key":"maintenance_request_v1","title":"Maintenance Request","division_id":"industry-solutions",
  "description":"Record a maintenance issue, require technician review, and record supervisor closure.",
  "steps":["request_recorded","technician_review","work_completed","supervisor_close"]},
 {"workflow_key":"release_gate_v1","title":"Product Release Gate","division_id":"governance-security",
  "description":"Record source, tests, security review, owner decision, and deployment evidence.",
  "steps":["artifact_recorded","tests_verified","security_review","owner_release_decision","deployment_verification"]}
]

def ensure_workflow_definitions(db_path:Path|str=DB_PATH)->int:
    stamp=now_iso();created=0
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        for item in WORKFLOW_TEMPLATES:
            cur=db.execute("""INSERT OR IGNORE INTO workflow_definitions
              (workflow_key,title,division_id,description,steps_json,version,created_at,updated_at)
              VALUES(?,?,?,?,?,'1.0',?,?)""",
              (item["workflow_key"],item["title"],item["division_id"],item["description"],canonical(item["steps"]),stamp,stamp))
            created+=cur.rowcount
    return created

def list_workflow_definitions(db_path:Path|str=DB_PATH)->list[dict[str,Any]]:
    ensure_workflow_definitions(db_path)
    with connect(db_path) as db:rows=db.execute("SELECT * FROM workflow_definitions ORDER BY division_id,title").fetchall()
    result=[]
    for row in rows:
        item=dict(row);item["steps"]=json.loads(item.pop("steps_json"));result.append(item)
    return result

def _safe_workflow_context(value:Any)->dict[str,Any]:
    if value is None:return {}
    if not isinstance(value,dict):raise ApiError(400,"context must be an object.")
    allowed={"summary","source_ref","record_ref","business_unit"}
    if set(value)-allowed:raise ApiError(400,"context allows only summary, source_ref, record_ref, and business_unit.")
    result={}
    for key,limit in (("summary",500),("source_ref",300),("record_ref",120),("business_unit",100)):
        if key in value:result[key]=clean_text(value[key],key,limit)
    return result

def start_workflow(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    key=clean_text(data.get("workflow_key"),"workflow_key",80,True)
    ensure_workflow_definitions(db_path)
    context=_safe_workflow_context(data.get("context",{}))
    notes=clean_text(data.get("notes"),"notes",500)
    rid=str(uuid.uuid4());stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        definition=db.execute("SELECT * FROM workflow_definitions WHERE workflow_key=?",(key,)).fetchone()
        if not definition:raise ApiError(404,"Workflow definition not found.")
        db.execute("""INSERT INTO workflow_runs(id,workflow_key,status,current_step_index,context_json,notes,created_at,updated_at)
          VALUES(?,?,'active',0,?,?,?,?)""",(rid,key,canonical(context),notes,stamp,stamp))
        append_audit(db,"workflow.started","workflow_run",rid,{"workflow_key":key,"context":context})
        row=dict(db.execute("SELECT * FROM workflow_runs WHERE id=?",(rid,)).fetchone())
    row["context"]=json.loads(row.pop("context_json"));row["steps"]=json.loads(definition["steps_json"])
    return row

def list_workflow_runs(db_path:Path|str=DB_PATH)->list[dict[str,Any]]:
    ensure_workflow_definitions(db_path)
    with connect(db_path) as db:
        rows=db.execute("""SELECT r.*,d.title,d.division_id,d.steps_json,d.version
          FROM workflow_runs r JOIN workflow_definitions d ON d.workflow_key=r.workflow_key
          ORDER BY r.created_at DESC LIMIT 200""").fetchall()
    result=[]
    for row in rows:
        item=dict(row);steps=json.loads(item.pop("steps_json"));item["steps"]=steps
        item["context"]=json.loads(item.pop("context_json"));item["current_step"]=steps[item["current_step_index"]] if item["current_step_index"]<len(steps) else "complete"
        result.append(item)
    return result

def act_on_workflow_run(run_id:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    action=clean_text(data.get("action"),"action",20,True)
    if action not in {"advance","block","resume","cancel"}:raise ApiError(400,"Action must be advance, block, resume, or cancel.")
    note=clean_text(data.get("note"),"note",500)
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("""SELECT r.*,d.steps_json FROM workflow_runs r JOIN workflow_definitions d
          ON d.workflow_key=r.workflow_key WHERE r.id=?""",(run_id,)).fetchone()
        if not row:raise ApiError(404,"Workflow run not found.")
        status=row["status"];index=row["current_step_index"];steps=json.loads(row["steps_json"])
        if action=="advance":
            if status!="active":raise ApiError(409,"Only an active workflow run can advance.")
            index+=1
            if index>=len(steps):status="completed"
        elif action=="block":
            if status!="active":raise ApiError(409,"Only an active workflow run can be blocked.")
            status="blocked"
        elif action=="resume":
            if status!="blocked":raise ApiError(409,"Only a blocked workflow run can resume.")
            status="active"
        elif action=="cancel":
            if status not in {"active","blocked"}:raise ApiError(409,"This workflow run cannot be cancelled.")
            status="cancelled"
        stamp=now_iso()
        db.execute("UPDATE workflow_runs SET status=?,current_step_index=?,notes=?,updated_at=? WHERE id=?",
          (status,index,note,stamp,run_id))
        append_audit(db,"workflow."+action,"workflow_run",run_id,{"action":action,"status":status,"step_index":index,"note":note})
        result=dict(db.execute("SELECT * FROM workflow_runs WHERE id=?",(run_id,)).fetchone())
        result["context"]=json.loads(result.pop("context_json"));result["steps"]=steps
        result["current_step"]=steps[index] if index<len(steps) else "complete"
        result["external_actions_executed"]=False
    return result


def create_knowledge_link(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    source=clean_text(data.get("from_doc_id"),"from_doc_id",64,True)
    target=clean_text(data.get("to_doc_id"),"to_doc_id",64,True)
    relation=clean_text(data.get("relation"),"relation",30,True)
    if source==target:raise ApiError(400,"A document cannot link to itself.")
    if relation not in KNOWLEDGE_RELATIONS:raise ApiError(400,"Unsupported knowledge relation.")
    rid=str(uuid.uuid4());stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        ids={r["id"] for r in db.execute("SELECT id FROM knowledge_docs WHERE id IN (?,?)",(source,target)).fetchall()}
        if source not in ids or target not in ids:raise ApiError(404,"Both documents must exist.")
        try:
            db.execute("INSERT INTO knowledge_links(id,from_doc_id,to_doc_id,relation,created_at) VALUES(?,?,?,?,?)",(rid,source,target,relation,stamp))
        except sqlite3.IntegrityError as exc:raise ApiError(409,"This document relationship already exists.") from exc
        append_audit(db,"knowledge.link.created","knowledge_link",rid,{"from_doc_id":source,"to_doc_id":target,"relation":relation})
        result=dict(db.execute("""SELECT l.*,a.title AS from_title,b.title AS to_title
          FROM knowledge_links l JOIN knowledge_docs a ON a.id=l.from_doc_id
          JOIN knowledge_docs b ON b.id=l.to_doc_id WHERE l.id=?""",(rid,)).fetchone())
    return result

def list_knowledge_links(db_path:Path|str=DB_PATH)->list[dict[str,Any]]:
    with connect(db_path) as db:
        rows=db.execute("""SELECT l.*,a.title AS from_title,b.title AS to_title
          FROM knowledge_links l JOIN knowledge_docs a ON a.id=l.from_doc_id
          JOIN knowledge_docs b ON b.id=l.to_doc_id ORDER BY l.created_at DESC LIMIT 250""").fetchall()
    return [dict(r) for r in rows]

def search_knowledge_graph(query:str,db_path:Path|str=DB_PATH)->dict[str,Any]:
    base=search_knowledge(query,db_path)
    matched={x["id"]:x for x in base["items"][:10]}
    if not matched:return {"query":query,"matches":[],"related":[],"method":"keyword_plus_one_hop_evidence_links",
      "disclaimer":"No matching local sources were found. This is not vector search or AI-generated analysis."}
    placeholders=",".join("?" for _ in matched)
    with connect(db_path) as db:
        links=db.execute(f"""SELECT l.id,l.from_doc_id,l.to_doc_id,l.relation,
          a.title AS from_title,a.source_ref AS from_source,b.title AS to_title,b.source_ref AS to_source,
          a.content AS from_content,b.content AS to_content
          FROM knowledge_links l JOIN knowledge_docs a ON a.id=l.from_doc_id
          JOIN knowledge_docs b ON b.id=l.to_doc_id
          WHERE l.from_doc_id IN ({placeholders}) OR l.to_doc_id IN ({placeholders})""",
          (*matched.keys(),*matched.keys())).fetchall()
    related={}
    edges=[]
    for link in links:
        source_match=link["from_doc_id"] in matched
        other_id=link["to_doc_id"] if source_match else link["from_doc_id"]
        if other_id not in matched:
            related[other_id]={"id":other_id,"title":link["to_title"] if source_match else link["from_title"],
              "source_ref":link["to_source"] if source_match else link["from_source"],
              "excerpt":(link["to_content"] if source_match else link["from_content"])[:500],
              "citation":"local-document:"+other_id}
        edges.append({"from_doc_id":link["from_doc_id"],"to_doc_id":link["to_doc_id"],"relation":link["relation"],
          "from_title":link["from_title"],"to_title":link["to_title"]})
    return {"query":query,"matches":list(matched.values()),"related":list(related.values())[:20],"edges":edges,
      "method":"keyword_plus_one_hop_evidence_links",
      "disclaimer":"Lexical matching plus one-hop manually curated document links. This is not vector search, GraphRAG, or AI inference. Review sources directly."}


def extract_document_fields(data:dict[str,Any])->dict[str,Any]:
    text=clean_text(data.get("document_text"),"document_text",20000,True)
    lowered=text.lower()
    if "invoice" in lowered:doc_type="invoice"
    elif "work order" in lowered or "work-order" in lowered:doc_type="work_order"
    else:doc_type="unknown"
    patterns={
      "document_number":r"(?im)^\s*(?:invoice|work\s*order)\s*(?:number|no\.?|#|id)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{2,40})\s*$",
      "document_date":r"(?im)^\s*(?:invoice\s+date|date)\s*:\s*(\d{4}-\d{2}-\d{2})\s*$",
      "due_date":r"(?im)^\s*(?:due\s+date|payment\s+due)\s*:\s*(\d{4}-\d{2}-\d{2})\s*$",
      "vendor":r"(?im)^\s*(?:vendor|supplier|company)\s*:\s*(.{2,120})\s*$",
      "total":r"(?im)^\s*(?:total|amount\s+due|balance\s+due)\s*:\s*\$?\s*([0-9,]+(?:\.[0-9]{2})?)\s*$"
    }
    fields={}
    for key,pattern in patterns.items():
        match=re.search(pattern,text)
        if match:
            value=match.group(1).strip()
            fields[key]=value
    required=("document_number","document_date","total")
    confidence=round(sum(1 for key in required if key in fields)/len(required),2)
    return {"document_type":doc_type,"fields":fields,"confidence_on_required_fields":confidence,
      "human_review_required":True,"saved_to_database":False,
      "disclaimer":"Deterministic text-pattern extraction only. Scanned-image OCR, legal/accounting validation, and AI inference are not performed. Check every field against the original document."}

def draft_support_reply(data:dict[str,Any])->dict[str,Any]:
    question=clean_text(data.get("question"),"question",1000,True)
    result=search_knowledge(question)
    matches=result.get("items",[])[:3]
    if matches:
        evidence="\n\n".join("- "+item["title"]+" ("+item["citation"]+"):\n  "+item["excerpt"] for item in matches)
        draft=("Thank you for your question. I reviewed the available internal reference material. "
               "The relevant documented information is:\n\n"+evidence+
               "\n\nI have not independently verified whether this material is current or complete. "
               "A team member should check the cited source and confirm any customer-specific details before sending.")
    else:
        evidence="No relevant local reference was found."
        draft=("Thank you for your question. I don't currently have a verified internal reference that answers it. "
               "A team member needs to review the request and confirm the correct answer before responding.")
    return {"question":question,"draft":draft,"sources":[{"title":x["title"],"source_ref":x["source_ref"],"citation":x["citation"]} for x in matches],
      "requires_human_review":True,"sent":False,"model_used":None,
      "disclaimer":"Deterministic local draft only. No AI model was called and no email, SMS, or customer message was sent."}


def _date_value(value:Any,field:str)->str:
    text=clean_text(value,field,10,True)
    try:
        from datetime import date
        date.fromisoformat(text)
    except ValueError: raise ApiError(400,field+" must use YYYY-MM-DD.")
    return text

def create_finance_entry(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    entry_type=clean_text(data.get("entry_type"),"entry_type",20,True)
    if entry_type not in {"inflow","outflow"}: raise ApiError(400,"entry_type must be inflow or outflow.")
    label=clean_text(data.get("label"),"label",140,True)
    category=clean_text(data.get("category"),"category",80,True)
    amount=data.get("amount_cents")
    if isinstance(amount,bool) or not isinstance(amount,int) or not 0<amount<=10_000_000_000: raise ApiError(400,"amount_cents must be a positive integer.")
    happened=_date_value(data.get("happened_on") or now_iso()[:10],"happened_on")
    source=clean_text(data.get("source","manual"),"source",30,True)
    if source not in {"manual","synthetic"}: raise ApiError(400,"source must be manual or synthetic.")
    notes=clean_text(data.get("notes"),"notes",500)
    revenue_class=clean_text(data.get("revenue_class","unknown"),"revenue_class",20,True)
    collection_state=clean_text(data.get("collection_state","unknown"),"collection_state",20,True)
    if revenue_class not in {"one_time","recurring","unknown"}:raise ApiError(400,"revenue_class must be one_time, recurring, or unknown.")
    if collection_state not in {"collected_manual","invoiced","pending","disputed","unknown"}:raise ApiError(400,"Invalid collection_state.")
    if entry_type=="outflow" and (revenue_class!="unknown" or collection_state!="unknown"):raise ApiError(400,"Revenue classification applies only to inflows.")
    rid=str(uuid.uuid4());stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO finance_entries(id,entry_type,label,category,amount_cents,happened_on,source,notes,revenue_class,collection_state,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(rid,entry_type,label,category,amount,happened,source,notes,revenue_class,collection_state,stamp))
        append_audit(db,"finance.entry.created","finance_entry",rid,{"entry_type":entry_type,"amount_cents":amount,"happened_on":happened,"source":source,"revenue_class":revenue_class,"collection_state":collection_state})
        result=dict(db.execute("SELECT * FROM finance_entries WHERE id=?",(rid,)).fetchone())
    return result

def finance_summary(start:str|None=None,end:str|None=None,db_path:Path|str=DB_PATH)->dict[str,Any]:
    if start:start=_date_value(start,"start")
    if end:end=_date_value(end,"end")
    if start and end and start>end: raise ApiError(400,"start must be on or before end.")
    clauses=[];params=[]
    if start:clauses.append("happened_on>=?");params.append(start)
    if end:clauses.append("happened_on<=?");params.append(end)
    where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
    with connect(db_path) as db:
        totals=db.execute("SELECT entry_type,COALESCE(SUM(amount_cents),0) total,COUNT(*) count FROM finance_entries"+where+" GROUP BY entry_type",params).fetchall()
        rows=db.execute("SELECT * FROM finance_entries"+where+" ORDER BY happened_on DESC,created_at DESC LIMIT 100",params).fetchall()
    sums={r["entry_type"]:{"amount_cents":r["total"],"count":r["count"]} for r in totals}
    inflows=sums.get("inflow",{}).get("amount_cents",0);outflows=sums.get("outflow",{}).get("amount_cents",0)
    return {"inflows_cents":inflows,"outflows_cents":outflows,"net_cents":inflows-outflows,
      "entry_count":sum(x["count"] for x in sums.values()),"by_type":sums,"items":[dict(r) for r in rows],
      "disclaimer":"Manual ledger totals only; not bank-verified balances, financial statements, or tax advice."}


def revenue_quality_summary(db_path:Path|str=DB_PATH)->dict[str,Any]:
    with connect(db_path) as db:
        classes=db.execute("SELECT revenue_class,collection_state,COALESCE(SUM(amount_cents),0) total,COUNT(*) count FROM finance_entries WHERE entry_type='inflow' GROUP BY revenue_class,collection_state ORDER BY total DESC").fetchall()
    class_totals={};state_totals={}
    for row in classes:
        class_totals[row["revenue_class"]]=class_totals.get(row["revenue_class"],0)+row["total"]
        state_totals[row["collection_state"]]=state_totals.get(row["collection_state"],0)+row["total"]
    return {"inflow_class_totals_cents":class_totals,"collection_state_totals_cents":state_totals,
      "items":[dict(r) for r in classes],"total_manual_inflows_cents":sum(class_totals.values()),
      "disclaimer":"Based only on manually entered ledger records. 'Collected manual' is not independently processor-verified; no bank or payment provider is connected."}

def expense_review_summary(db_path:Path|str=DB_PATH)->dict[str,Any]:
    with connect(db_path) as db:
        rows=db.execute("SELECT category,COALESCE(SUM(amount_cents),0) total,COUNT(*) count FROM finance_entries WHERE entry_type='outflow' GROUP BY category ORDER BY total DESC").fetchall()
    total=sum(r["total"] for r in rows)
    items=[{"category":r["category"],"amount_cents":r["total"],"count":r["count"],
            "share_of_recorded_outflows":round(r["total"]/total,4) if total else 0} for r in rows]
    return {"recorded_outflows_cents":total,"categories":items,
      "disclaimer":"Manual ledger review only. Categories and amounts may be incomplete and are not bank-verified."}

def runway_scenario(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    cash=data.get("available_cash_cents")
    period=data.get("period_days",30)
    if isinstance(cash,bool) or not isinstance(cash,int) or not 0<=cash<=10_000_000_000:raise ApiError(400,"available_cash_cents must be a non-negative integer.")
    if isinstance(period,bool) or not isinstance(period,int) or not 7<=period<=365:raise ApiError(400,"period_days must be between 7 and 365.")
    start=(datetime.now(timezone.utc)-timedelta(days=period)).date().isoformat()
    with connect(db_path) as db:
        totals=db.execute("SELECT entry_type,COALESCE(SUM(amount_cents),0) total FROM finance_entries WHERE happened_on>=? AND happened_on<=? GROUP BY entry_type",(start,now_iso()[:10])).fetchall()
    by={r["entry_type"]:r["total"] for r in totals}
    inflows=by.get("inflow",0);outflows=by.get("outflow",0);net_burn=outflows-inflows
    monthly_burn=max(0,round(net_burn*30/period))
    runway=None if monthly_burn<=0 else round(cash/monthly_burn,2)
    return {"period_days":period,"available_cash_cents":cash,"recorded_inflows_cents":inflows,
      "recorded_outflows_cents":outflows,"net_burn_for_period_cents":net_burn,
      "estimated_monthly_net_burn_cents":monthly_burn,"runway_months_at_assumed_cash_and_burn":runway,
      "disclaimer":"Scenario only. Available cash is manually supplied and ledger activity may be incomplete; not bank-verified or financial advice."}


def forecast_cash(data:dict[str,Any])->dict[str,Any]:
    def cents(key:str)->int:
        value=data.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=10_000_000_000: raise ApiError(400,key+" must be a non-negative integer in cents.")
        return value
    opening=cents("opening_cash_cents");inflow=cents("weekly_inflows_cents");outflow=cents("weekly_outflows_cents")
    start=_date_value(data.get("start_date") or now_iso()[:10],"start_date")
    balance=opening;weeks=[];lowest=opening;lowest_week=0
    for i in range(1,14):
        balance=balance+inflow-outflow
        if balance<lowest:lowest=balance;lowest_week=i
        weeks.append({"week":i,"closing_cash_cents":balance,"net_change_cents":inflow-outflow})
    burn=outflow-inflow
    runway=None if burn<=0 else round(opening/burn,2)
    return {"opening_cash_cents":opening,"weekly_inflows_cents":inflow,"weekly_outflows_cents":outflow,
      "weekly_net_cents":inflow-outflow,"week_13_closing_cash_cents":balance,"lowest_cash_cents":lowest,
      "lowest_cash_week":lowest_week,"runway_weeks_at_assumed_net_burn":runway,"weeks":weeks,
      "disclaimer":"Scenario only. Assumptions are not bank-connected or processor-verified. Not financial, tax, or investment advice."}

def create_knowledge_doc(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    title=clean_text(data.get("title"),"title",180,True)
    division=clean_text(data.get("division_id"),"division_id",60,True)
    if division not in DIVISION_IDS: raise ApiError(400,"Unknown division_id.")
    source=clean_text(data.get("source_ref"),"source_ref",300,True)
    content=clean_text(data.get("content"),"content",20000,True)
    rid=str(uuid.uuid4());stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO knowledge_docs(id,title,division_id,source_ref,content,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
          (rid,title,division,source,content,stamp,stamp))
        append_audit(db,"knowledge.document.created","knowledge_doc",rid,{"title":title,"division_id":division,"source_ref":source,"content_sha256":hashlib.sha256(content.encode()).hexdigest()})
        result=dict(db.execute("SELECT id,title,division_id,source_ref,created_at,updated_at FROM knowledge_docs WHERE id=?",(rid,)).fetchone())
    return result

def search_knowledge(query:str,db_path:Path|str=DB_PATH)->dict[str,Any]:
    query=clean_text(query,"q",200,True)
    terms=[x.lower() for x in query.split() if len(x)>1]
    if not terms: raise ApiError(400,"Search query needs at least one term longer than one character.")
    with connect(db_path) as db: rows=db.execute("SELECT id,title,division_id,source_ref,content,created_at FROM knowledge_docs ORDER BY created_at DESC LIMIT 500").fetchall()
    found=[]
    for row in rows:
        hay=(row["title"]+" "+row["content"]).lower()
        score=sum(hay.count(term) for term in terms)
        if score:
            excerpt=row["content"][:500]
            found.append({"id":row["id"],"title":row["title"],"division_id":row["division_id"],"source_ref":row["source_ref"],
              "score":score,"excerpt":excerpt,"citation":"local-document:"+row["id"]})
    found.sort(key=lambda item:(-item["score"],item["title"]))
    return {"query":query,"items":found[:50],"method":"local_keyword_search","disclaimer":"Search is lexical, not an AI model. Verify the cited source before relying on a result."}

def create_work_item(data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    division=clean_text(data.get("division_id"),"division_id",60,True)
    if division not in {"ai-operations-studio","industry-solutions","infrastructure","governance-security"}: raise ApiError(400,"Work items must use an operations, industry, infrastructure, or governance division.")
    wtype=clean_text(data.get("workflow_type"),"workflow_type",60,True)
    if wtype not in {"document_intake","support_review","dispatch_exception","maintenance_request","shift_handoff","release_task","security_finding","workflow_map"}: raise ApiError(400,"Unsupported workflow_type.")
    title=clean_text(data.get("title"),"title",180,True);description=clean_text(data.get("description"),"description",1500)
    priority=clean_text(data.get("priority","normal"),"priority",20,True)
    if priority not in {"low","normal","high","critical"}: raise ApiError(400,"Invalid priority.")
    due=clean_text(data.get("due_date"),"due_date",10)
    if due:_date_value(due,"due_date")
    rid=str(uuid.uuid4());stamp=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO work_items(id,division_id,workflow_type,title,description,priority,status,due_date,created_at,updated_at)
          VALUES(?,?,?,?,?,?,'open',?,?,?)""",(rid,division,wtype,title,description,priority,due,stamp,stamp))
        append_audit(db,"work_item.created","work_item",rid,{"division_id":division,"workflow_type":wtype,"priority":priority})
        result=dict(db.execute("SELECT * FROM work_items WHERE id=?",(rid,)).fetchone())
    return result

def update_work_item(rid:str,data:dict[str,Any],db_path:Path|str=DB_PATH)->dict[str,Any]:
    if not data or set(data)-{"status","priority","description"}: raise ApiError(400,"Only status, priority, and description may be updated.")
    updates={}
    if "status" in data:
        status=clean_text(data["status"],"status",20,True)
        if status not in {"open","in_progress","blocked","done"}: raise ApiError(400,"Invalid work item status.")
        updates["status"]=status
    if "priority" in data:
        priority=clean_text(data["priority"],"priority",20,True)
        if priority not in {"low","normal","high","critical"}: raise ApiError(400,"Invalid priority.")
        updates["priority"]=priority
    if "description" in data:updates["description"]=clean_text(data["description"],"description",1500)
    updates["updated_at"]=now_iso()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM work_items WHERE id=?",(rid,)).fetchone(): raise ApiError(404,"Work item not found.")
        db.execute("UPDATE work_items SET "+",".join(k+"=?" for k in updates)+" WHERE id=?",(*updates.values(),rid))
        append_audit(db,"work_item.updated","work_item",rid,updates)
        result=dict(db.execute("SELECT * FROM work_items WHERE id=?",(rid,)).fetchone())
    return result

def system_diagnostics(db_path:Path|str=DB_PATH)->dict[str,Any]:
    with connect(db_path) as db:
        mode=db.execute("PRAGMA journal_mode").fetchone()[0]
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        integrity=db.execute("PRAGMA quick_check").fetchone()[0]
    catalog=load_catalog();offer_count=sum(len(d.get("offers",[])) for d in catalog["divisions"])
    return {"python":sys.version.split()[0],"sqlite":sqlite3.sqlite_version,"database_journal_mode":mode,
      "database_integrity":integrity,"tables":tables,"division_count":len(catalog["divisions"]),"offer_count":offer_count,
      "external_integrations_enabled":False,"deployment_state":"local_only","backup_path":"platform/backups (local only)"}

def create_local_backup(db_path:Path|str=DB_PATH,backup_dir:Path|str|None=None)->dict[str,Any]:
    directory=Path(backup_dir) if backup_dir is not None else Path(db_path).parent/"backups"
    directory.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ%f")
    destination=directory/("garcar-"+stamp+".sqlite3")
    source=connect(db_path);target=sqlite3.connect(destination)
    try:source.backup(target)
    finally:target.close();source.close()
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    with connect(db_path) as db:
        append_audit(db,"system.backup.created","backup",destination.name,{"sha256":digest,"bytes":destination.stat().st_size})
    return {"filename":destination.name,"bytes":destination.stat().st_size,"sha256":digest,"location":str(directory),"external_upload":False}

def _safe_backup_path(filename:str,backup_dir:Path|str|None=None,db_path:Path|str=DB_PATH)->Path:
    name=clean_text(filename,"filename",120,True)
    if Path(name).name!=name or not name.startswith("garcar-") or not name.endswith(".sqlite3"):
        raise ApiError(400,"Invalid backup filename.")
    directory=Path(backup_dir) if backup_dir is not None else Path(db_path).parent/"backups"
    path=(directory/name).resolve()
    if path.parent!=directory.resolve():raise ApiError(400,"Invalid backup path.")
    return path

def verify_local_backup(filename:str,db_path:Path|str=DB_PATH,backup_dir:Path|str|None=None)->dict[str,Any]:
    path=_safe_backup_path(filename,backup_dir,db_path)
    if not path.is_file():raise ApiError(404,"Backup file not found.")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with connect(db_path) as db:
        row=db.execute("SELECT payload_json FROM audit_events WHERE event_type='system.backup.created' AND entity_id=? ORDER BY seq DESC LIMIT 1",(path.name,)).fetchone()
    if not row:raise ApiError(404,"Backup audit reference not found.")
    payload=json.loads(row["payload_json"])
    checksum_match=hmac.compare_digest(digest,payload.get("sha256",""))
    backup=None
    try:
        backup=sqlite3.connect(f"file:{path}?mode=ro",uri=True)
        integrity=backup.execute("PRAGMA quick_check").fetchone()[0]
    except sqlite3.Error as exc:raise ApiError(422,"Backup SQLite integrity check failed.") from exc
    finally:
        if backup is not None:backup.close()
    valid=checksum_match and integrity=="ok"
    return {"filename":path.name,"valid":valid,"checksum_match":checksum_match,"database_integrity":integrity,
      "bytes":path.stat().st_size,"sha256":digest,"restore_performed":False}

def list_local_backups(db_path:Path|str=DB_PATH,backup_dir:Path|str|None=None)->dict[str,Any]:
    directory=Path(backup_dir) if backup_dir is not None else Path(db_path).parent/"backups"
    directory.mkdir(parents=True,exist_ok=True)
    with connect(db_path) as db:
        rows=db.execute("SELECT entity_id,payload_json,occurred_at FROM audit_events WHERE event_type='system.backup.created' ORDER BY seq DESC LIMIT 50").fetchall()
    items=[]
    for row in rows:
        path=_safe_backup_path(row["entity_id"],directory,db_path)
        exists=path.is_file()
        item={"filename":row["entity_id"],"created_at":row["occurred_at"],"exists":exists}
        if exists:
            item["bytes"]=path.stat().st_size
            item["sha256_recorded"]=json.loads(row["payload_json"]).get("sha256","")
        items.append(item)
    return {"items":items,"location":str(directory),"external_copy":False,
      "disclaimer":"Local backup inventory only. This is not off-site or disaster-recovery protection."}


class Handler(BaseHTTPRequestHandler):
    server_version="GarcarLocal/1.0"
    def log_message(self,fmt,*args):
        message=fmt%args
        if self.path.startswith("/digital/download/"):
            message=message.replace(self.path,"/digital/download/[TOKEN-REDACTED]")
        sys.stderr.write("[garcar] "+message+"\\n")
    def send_body(self,status:int,body:Any,ctype:str="application/json"):
        raw=body if isinstance(body,bytes) else body if isinstance(body,str) else json.dumps(body,ensure_ascii=False)
        if isinstance(raw,str):raw=raw.encode()
        self.send_response(status);self.send_header("Content-Type",ctype+"; charset=utf-8");self.send_header("Content-Length",str(len(raw)))
        self.send_header("X-Content-Type-Options","nosniff");self.send_header("Referrer-Policy","no-referrer");self.send_header("Cache-Control","no-store")
        if ctype=="text/html": self.send_header("Content-Security-Policy","default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(raw)
    def send_file(self,path:Path,download_name:str)->None:
        raw=path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type","application/pdf")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Content-Disposition",'attachment; filename="'+download_name.replace('"',"")+'"')
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Cache-Control","no-store, private")
        self.send_header("Pragma","no-cache")
        self.send_header("Referrer-Policy","no-referrer")
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        try:n=int(self.headers.get("Content-Length","0"))
        except ValueError:raise ApiError(400,"Invalid content length.")
        if n<1 or n>65536:raise ApiError(400,"JSON body must be 1–65536 bytes.")
        try:data=json.loads(self.rfile.read(n))
        except (json.JSONDecodeError,UnicodeDecodeError) as e:raise ApiError(400,"Invalid JSON body.") from e
        if not isinstance(data,dict):raise ApiError(400,"JSON body must be an object.")
        return data
    def auth(self):
        if not hmac.compare_digest(self.headers.get("X-Admin-Token",""),self.server.admin_token):raise ApiError(401,"Missing or invalid local admin token.")
    def route(self):
        p=urlparse(self.path);return p.path,parse_qs(p.query)
    def do_GET(self):
        try:
            path,q=self.route()
            if path in {"/","/index.html"}:return self.send_body(200,(HERE/"index.html").read_text(encoding="utf-8"),"text/html")
            if path=="/api/health":return self.send_body(200,{"ok":True,"mode":"local_only","external_actions_enabled":False,"database":"sqlite_wal"})
            if path=="/api/catalog":return self.send_body(200,load_catalog())

            if path.startswith("/digital/download/"):
                parts=path.split("/")
                if len(parts)!=4 or not parts[3]:raise ApiError(404,"Download route not found.")
                from digital_delivery import consume_download_token,ASSET_FILES
                asset,meta=consume_download_token(parts[3])
                self.send_file(asset,ASSET_FILES[meta["product_id"]])
                return

            self.auth()

            if path=="/api/digital/health":
                from digital_delivery import digital_delivery_health
                return self.send_body(200,digital_delivery_health(DB_PATH))
            if path=="/api/digital/catalog":
                from digital_delivery import list_digital_products
                return self.send_body(200,{"items":list_digital_products(DB_PATH)})
            if path=="/api/digital/orders":
                from digital_delivery import list_digital_orders
                return self.send_body(200,{"items":list_digital_orders(DB_PATH)})
            if path=="/api/digital/entitlements":
                from digital_delivery import list_digital_entitlements
                return self.send_body(200,{"items":list_digital_entitlements(DB_PATH)})

            if path=="/api/dashboard":return self.send_body(200,dashboard())
            if path=="/api/leads":return self.send_body(200,{"items":list_records("leads")})
            if path=="/api/opportunities":return self.send_body(200,{"items":list_records("opportunities")})
            if path=="/api/approvals":return self.send_body(200,{"items":list_records("approvals")})
            if path=="/api/interviews":return self.send_body(200,{"items":list_records("validation_interviews")})

            if path=="/api/finance/entries":return self.send_body(200,{"items":list_records("finance_entries")})
            if path=="/api/finance/summary":return self.send_body(200,finance_summary(q.get("start",[None])[0],q.get("end",[None])[0]))
            if path=="/api/finance/quality":return self.send_body(200,revenue_quality_summary())
            if path=="/api/finance/expense-review":return self.send_body(200,expense_review_summary())
            if path=="/api/knowledge/docs":return self.send_body(200,{"items":list_records("knowledge_docs")})
            if path=="/api/knowledge/search":return self.send_body(200,search_knowledge(q.get("q",[""])[0]))
            if path=="/api/knowledge/links":return self.send_body(200,{"items":list_knowledge_links()})
            if path=="/api/knowledge/graph-search":return self.send_body(200,search_knowledge_graph(q.get("q",[""])[0]))
            if path=="/api/work-items":return self.send_body(200,{"items":list_records("work_items")})
            if path=="/api/workflows/definitions":return self.send_body(200,{"items":list_workflow_definitions()})
            if path=="/api/workflows/runs":return self.send_body(200,{"items":list_workflow_runs()})
            if path=="/api/product-readiness":return self.send_body(200,list_product_readiness())
            if path=="/api/system/diagnostics":return self.send_body(200,system_diagnostics())
            if path=="/api/system/backups":return self.send_body(200,list_local_backups())

            if path=="/api/audit/verify":return self.send_body(200,verify_ledger())
            if path=="/api/audit":
                with connect() as db:rows=db.execute("SELECT seq,event_type,entity_type,entity_id,actor,occurred_at,previous_hash,event_hash FROM audit_events ORDER BY seq DESC LIMIT 100").fetchall()
                return self.send_body(200,{"items":[dict(r) for r in rows]})
            if path=="/api/simulate/lead-value":
                try:d={k:float(q.get(k,[str(v)])[0]) for k,v in {"inbound_leads":100,"missed_rate":.2,"recovery_of_missed":.5,"booking_rate":.3,"average_job_value":1500}.items()}
                except ValueError:raise ApiError(400,"Calculator inputs must be numeric.")
                return self.send_body(200,simulate_lead_value(d))
            return self.send_body(404,{"error":"Route not found."})
        except ApiError as e:self.send_body(e.status,{"error":e.message})
        except Exception as e:sys.stderr.write("[garcar] GET error "+repr(e)+"\n");self.send_body(500,{"error":"Internal server error."})
    def do_POST(self):
        try:

            self.auth();path,_=self.route();data=self.read_json()
            if path=="/api/digital/test-checkout":
                from digital_delivery import create_test_checkout
                return self.send_body(201,create_test_checkout(data,DB_PATH))
            if path=="/api/digital/test-payment":
                from digital_delivery import simulate_test_payment
                order_id=clean_text(data.get("order_id"),"order_id",100,True)
                return self.send_body(200,simulate_test_payment(order_id,DB_PATH))
            if path=="/api/digital/test-refund":
                from digital_delivery import simulate_test_refund
                order_id=clean_text(data.get("order_id"),"order_id",100,True)
                return self.send_body(200,simulate_test_refund(order_id,DB_PATH))

            if path=="/api/leads":return self.send_body(201,create_lead(data))
            if path=="/api/opportunities":return self.send_body(201,create_opportunity(data))
            if path=="/api/interviews":return self.send_body(201,create_interview(data))

            if path=="/api/finance/entries":return self.send_body(201,create_finance_entry(data))
            if path=="/api/finance/forecast":return self.send_body(200,forecast_cash(data))
            if path=="/api/finance/runway":return self.send_body(200,runway_scenario(data))
            if path=="/api/knowledge/docs":return self.send_body(201,create_knowledge_doc(data))
            if path=="/api/knowledge/links":return self.send_body(201,create_knowledge_link(data))
            if path=="/api/work-items":return self.send_body(201,create_work_item(data))
            if path=="/api/workflows/runs":return self.send_body(201,start_workflow(data))
            if path=="/api/documents/extract":return self.send_body(200,extract_document_fields(data))
            if path=="/api/support/draft":return self.send_body(200,draft_support_reply(data))
            if len(path.strip("/").split("/"))==5 and path.strip("/").split("/")[0:2]==["api","workflows"] and path.strip("/").split("/")[2]=="runs" and path.strip("/").split("/")[4]=="action":
                parts=path.strip("/").split("/");return self.send_body(200,act_on_workflow_run(parts[3],data))
            if len(path.strip("/").split("/"))==4 and path.strip("/").split("/")[0:2]==["api","product-readiness"] and path.strip("/").split("/")[3]=="update":
                parts=path.strip("/").split("/");return self.send_body(200,update_product_readiness(parts[2],data))
            if path=="/api/system/backup":return self.send_body(201,create_local_backup())
            if path=="/api/system/backup/verify":return self.send_body(200,verify_local_backup(clean_text(data.get("filename"),"filename",120,True)))

            if path=="/api/approvals":return self.send_body(201,create_approval(data))
            parts=path.strip("/").split("/")
            if len(parts)==4 and parts[:2]==["api","leads"] and parts[3]=="update":return self.send_body(200,update_lead(parts[2],data))
            if len(parts)==4 and parts[:2]==["api","opportunities"] and parts[3]=="update":return self.send_body(200,update_opportunity(parts[2],data))
            if len(parts)==4 and parts[:2]==["api","work-items"] and parts[3]=="update":return self.send_body(200,update_work_item(parts[2],data))
            if len(parts)==4 and parts[:2]==["api","approvals"] and parts[3]=="decision":return self.send_body(200,decide_approval(parts[2],data))
            return self.send_body(404,{"error":"Route not found."})
        except ApiError as e:self.send_body(e.status,{"error":e.message})
        except Exception as e:sys.stderr.write("[garcar] POST error "+repr(e)+"\n");self.send_body(500,{"error":"Internal server error."})

class LocalServer(ThreadingHTTPServer):
    daemon_threads=True;allow_reuse_address=True
    def __init__(self,address,token):super().__init__(address,Handler);self.admin_token=token

def main():
    parser=argparse.ArgumentParser(description="Garcar local operating console")
    parser.add_argument("--port",type=int,default=int(os.environ.get("GARCAR_PORT","8788")))
    parser.add_argument("--demo",action="store_true",help="Create synthetic demo records if database is empty.")
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error("port must be 1024–65535")
    init_db()
    if args.demo:print("Synthetic demo leads inserted:",demo_seed())
    token=os.environ.get("GARCAR_ADMIN_TOKEN") or secrets.token_urlsafe(32)
    print("Garcar local console: http://127.0.0.1:"+str(args.port))
    print("Local admin token (keep private): "+token)
    print("Email/SMS, payments, deployments, integrations and customer CRM writes are disabled.")
    httpd=LocalServer(("127.0.0.1",args.port),token)
    try:httpd.serve_forever()
    except KeyboardInterrupt:print("\nStopping local console.")
    finally:httpd.server_close()

if __name__=="__main__":main()
