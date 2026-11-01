#!/usr/bin/env python3
"""Loopback-only HTTP smoke test using a temporary database and synthetic records."""
from __future__ import annotations
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent
TOKEN="garcar-smoke-test-token-not-for-production"

def free_port()->int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return int(sock.getsockname()[1])

def request(base:str,path:str,method:str="GET",payload:dict|None=None,authenticated:bool=True):
    data=None if payload is None else json.dumps(payload).encode()
    headers={"Content-Type":"application/json"}
    if authenticated:headers["X-Admin-Token"]=TOKEN
    req=urllib.request.Request(base+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=4) as response:
            raw=response.read()
            return response.status,json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw=exc.read()
        try:body=json.loads(raw)
        except Exception:body={"raw":raw.decode("utf-8","replace")}
        return exc.code,body

def main()->int:
    port=free_port()
    with tempfile.TemporaryDirectory(prefix="garcar-smoke-") as temp:
        env=os.environ.copy()
        env["GARCAR_DB_PATH"]=str(Path(temp)/"smoke.sqlite3")
        env["GARCAR_ADMIN_TOKEN"]=TOKEN
        proc=subprocess.Popen(
            [sys.executable,str(HERE/"server.py"),"--port",str(port)],
            cwd=HERE,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True
        )
        base=f"http://127.0.0.1:{port}"
        checks=[]
        try:
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if proc.poll() is not None:
                    out,err=proc.communicate()
                    raise RuntimeError("Server exited before health check.\n"+out+"\n"+err)
                try:
                    code,health=request(base,"/api/health",authenticated=False)
                    if code==200 and health.get("ok"):break
                except Exception:pass
                time.sleep(.15)
            else:raise RuntimeError("Local server did not become healthy within 12 seconds.")

            code,denied=request(base,"/api/dashboard",authenticated=False)
            checks.append(("protected dashboard rejects missing token",code==401))
            code,catalog=request(base,"/api/catalog",authenticated=False)
            offers=[o for d in catalog.get("divisions",[]) for o in d.get("offers",[])]
            checks.append(("public catalog has 8 divisions and 46 offers",code==200 and len(catalog.get("divisions",[]))==8 and len(offers)==46))

            code,lead=request(base,"/api/leads","POST",{
              "company":"SMOKE DEMO HVAC","category":"HVAC","source":"synthetic_demo",
              "service_need":"Synthetic missed lead example","estimated_value_cents":100000
            })
            lead_id=lead.get("id")
            checks.append(("create lead",code==201 and bool(lead_id)))

            code,deal=request(base,"/api/opportunities","POST",{
              "lead_id":lead_id,"offer_id":"RA-001","amount_cents":49700,"stage":"discovery",
              "next_step":"Synthetic smoke test only"
            })
            checks.append(("create offer-linked opportunity",code==201 and deal.get("offer_id")=="RA-001"))

            code,entry=request(base,"/api/finance/entries","POST",{
              "entry_type":"inflow","label":"Synthetic receipt","category":"demo",
              "amount_cents":10000,"source":"synthetic"
            })
            code2,summary=request(base,"/api/finance/summary")
            checks.append(("manual finance ledger and summary",code==201 and code2==200 and summary.get("inflows_cents")==10000))


            code,quality=request(base,"/api/finance/quality")
            code2,expenses=request(base,"/api/finance/expense-review")
            checks.append(("revenue quality and expense review APIs",code==200 and code2==200 and "disclaimer" in quality and "categories" in expenses))

            code,runway=request(base,"/api/finance/runway","POST",{"available_cash_cents":100000,"period_days":30})
            checks.append(("manual cash runway scenario",code==200 and runway.get("available_cash_cents")==100000))

            code,forecast=request(base,"/api/finance/forecast","POST",{
              "opening_cash_cents":100000,"weekly_inflows_cents":50000,"weekly_outflows_cents":40000
            })
            checks.append(("13-week forecast",code==200 and len(forecast.get("weeks",[]))==13))

            code,doc=request(base,"/api/knowledge/docs","POST",{
              "title":"Smoke test SOP","division_id":"revenue-automation","source_ref":"synthetic:test-fixture",
              "content":"A measured lead response process names an owner and records the response time."
            })
            code2,found=request(base,"/api/knowledge/search?q=lead%20response")
            checks.append(("source-linked local knowledge search",code==201 and code2==200 and bool(found.get("items"))))



            code,doc2=request(base,"/api/knowledge/docs","POST",{
              "title":"After-hours owner SOP","division_id":"revenue-automation","source_ref":"synthetic:after-hours",
              "content":"After-hours enquiries are routed to the on-call owner."
            })
            code2,link=request(base,"/api/knowledge/links","POST",{
              "from_doc_id":doc.get("id"),"to_doc_id":doc2.get("id"),"relation":"supports"
            })
            code3,graph=request(base,"/api/knowledge/graph-search?q=lead%20owner")
            checks.append(("evidence graph links and one-hop search",code==201 and code2==201 and code3==200 and bool(graph.get("edges"))))

            code,extracted=request(base,"/api/documents/extract","POST",{
              "document_text":"Invoice Number: INV-TEST-123\nInvoice Date: 2026-11-01\nVendor: Synthetic Supplier\nTotal: $125.00"
            })
            checks.append(("document intake extraction requires human review",code==200 and extracted.get("human_review_required") is True and extracted.get("saved_to_database") is False))

            code,draft=request(base,"/api/support/draft","POST",{"question":"How is lead response tracked?"})
            checks.append(("support draft remains unsent and requires review",code==200 and draft.get("sent") is False and draft.get("requires_human_review") is True))

            code,work=request(base,"/api/work-items","POST",{
              "division_id":"industry-solutions","workflow_type":"dispatch_exception",
              "title":"Synthetic dispatch exception","priority":"normal"
            })
            checks.append(("industry operations queue",code==201 and work.get("status")=="open"))


            code,definitions=request(base,"/api/workflows/definitions")
            code2,run=request(base,"/api/workflows/runs","POST",{
              "workflow_key":"lead_response_v1","context":{"summary":"Synthetic lead response workflow"}
            })
            code3,advanced=request(base,"/api/workflows/runs/"+run.get("id","")+"/action","POST",{"action":"advance"})
            checks.append(("workflow template and controlled state transition",code==200 and len(definitions.get("items",[]))==6 and code2==201 and code3==200 and advanced.get("external_actions_executed") is False))

            code,readiness=request(base,"/api/product-readiness")
            checks.append(("46-offer readiness register",code==200 and readiness.get("total")==46))

            code,approval=request(base,"/api/approvals","POST",{
              "action_type":"email.send","resource":"synthetic recipient only",
              "scope":"Smoke test; no message is sent."
            })
            code2,decision=request(base,"/api/approvals/"+approval.get("id","")+"/decision","POST",{
              "decision":"approved","comment":"Smoke test decision only."
            })
            checks.append(("approval is recorded without execution",code==201 and code2==200 and decision.get("execution_performed") is False))


            code,backup=request(base,"/api/system/backup","POST",{})
            code2,backup_list=request(base,"/api/system/backups")
            code3,verified=request(base,"/api/system/backup/verify","POST",{"filename":backup.get("filename","")})
            checks.append(("local backup inventory and checksum verification",code==201 and code2==200 and code3==200 and verified.get("valid") is True))

            code,diagnostics=request(base,"/api/system/diagnostics")
            checks.append(("database and catalog diagnostics",code==200 and diagnostics.get("database_integrity")=="ok"))
            code,ledger=request(base,"/api/audit/verify")
            checks.append(("audit hash chain verifies",code==200 and ledger.get("valid") is True))

            failed=[name for name,ok in checks if not ok]
            for name,ok in checks:
                print(("PASS" if ok else "FAIL")+" — "+name)
            print(f"\n{len(checks)-len(failed)}/{len(checks)} smoke checks passed.")
            if failed:
                print("Failures: "+", ".join(failed))
                return 1
            print("All records were synthetic and stored only in a temporary database.")
            return 0
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)

if __name__=="__main__":
    raise SystemExit(main())
