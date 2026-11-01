import tempfile
import unittest
from unittest import mock
from pathlib import Path
from server import ApiError,create_approval,create_interview,create_lead,create_opportunity,decide_approval,init_db,simulate_lead_value,verify_ledger,offer_index

class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"test.sqlite3"
        init_db(self.db)
    def tearDown(self):self.tmp.cleanup()
    def lead(self):
        return create_lead({"company":"Synthetic HVAC","category":"HVAC","source":"test_fixture","estimated_value_cents":125000},self.db)
    def test_create_lead_and_verify_chain(self):
        lead=self.lead()
        self.assertEqual(lead["status"],"new")
        self.assertTrue(verify_ledger(self.db)["valid"])
    def test_negative_lead_value_rejected(self):
        with self.assertRaises(ApiError):
            create_lead({"company":"Bad","category":"HVAC","source":"test","estimated_value_cents":-1},self.db)
    def test_opportunity_must_reference_real_lead_and_catalog_offer(self):
        lead=self.lead()
        deal=create_opportunity({"lead_id":lead["id"],"offer_id":"RA-001","amount_cents":49700,"stage":"discovery"},self.db)
        self.assertEqual(deal["offer_id"],"RA-001")
        with self.assertRaises(ApiError):
            create_opportunity({"lead_id":lead["id"],"offer_id":"FAKE","amount_cents":100},self.db)
    def test_decision_does_not_execute_action(self):
        item=create_approval({"action_type":"email.send","resource":"one reviewed message","scope":"single opted-in recipient"},self.db)
        result=decide_approval(item["id"],{"decision":"approved"},self.db)
        self.assertFalse(result["execution_performed"])
        self.assertEqual(result["status"],"approved")
    def test_unsupported_approval_action_rejected(self):
        with self.assertRaises(ApiError):create_approval({"action_type":"shell.execute","resource":"host","scope":"all"},self.db)
    def test_scenario_math(self):
        out=simulate_lead_value({"inbound_leads":100,"missed_rate":.2,"recovery_of_missed":.5,"booking_rate":.3,"average_job_value":1000})
        self.assertEqual(out["additional_contacted_leads_scenario"],10)
        self.assertEqual(out["expected_bookings_scenario"],3)
        self.assertEqual(out["illustrative_gross_job_value_scenario"],3000)
    def test_canonical_catalog_has_46_products(self):
        self.assertEqual(len(offer_index()),46)
    def test_interview_ledger(self):
        create_interview({"market":"home services","product_id":"RA-001","source":"voluntary interview"},self.db)
        self.assertTrue(verify_ledger(self.db)["valid"])
    def test_hash_chain_detects_tampering(self):
        self.lead()
        import sqlite3
        db=sqlite3.connect(self.db)
        db.execute("UPDATE audit_events SET payload_json='{}' WHERE seq=1")
        db.commit();db.close()
        self.assertFalse(verify_ledger(self.db)["valid"])


    def test_finance_ledger_and_summary(self):
        from server import create_finance_entry,finance_summary
        create_finance_entry({"entry_type":"inflow","label":"Synthetic invoice","category":"sales","amount_cents":100000,"source":"synthetic"},self.db)
        create_finance_entry({"entry_type":"outflow","label":"Synthetic expense","category":"tools","amount_cents":25000,"source":"manual"},self.db)
        summary=finance_summary(db_path=self.db)
        self.assertEqual(summary["inflows_cents"],100000)
        self.assertEqual(summary["outflows_cents"],25000)
        self.assertEqual(summary["net_cents"],75000)
    def test_cash_forecast_is_thirteen_weeks(self):
        from server import forecast_cash
        result=forecast_cash({"opening_cash_cents":100000,"weekly_inflows_cents":50000,"weekly_outflows_cents":40000})
        self.assertEqual(len(result["weeks"]),13)
        self.assertEqual(result["week_13_closing_cash_cents"],230000)
        self.assertIn("Not financial",result["disclaimer"])
    def test_knowledge_doc_search_has_local_citation(self):
        from server import create_knowledge_doc,search_knowledge
        doc=create_knowledge_doc({"title":"Lead response SOP","division_id":"revenue-automation","source_ref":"docs/lead-response.md","content":"A fast lead response needs a clear owner and a measured response time."},self.db)
        result=search_knowledge("lead response",self.db)
        self.assertEqual(result["items"][0]["id"],doc["id"])
        self.assertTrue(result["items"][0]["citation"].startswith("local-document:"))
    def test_industry_work_item_lifecycle(self):
        from server import create_work_item,update_work_item
        item=create_work_item({"division_id":"industry-solutions","workflow_type":"dispatch_exception","title":"Synthetic delayed shipment","priority":"high"},self.db)
        changed=update_work_item(item["id"],{"status":"in_progress"},self.db)
        self.assertEqual(changed["status"],"in_progress")
    def test_system_diagnostics_sees_full_catalog(self):
        from server import system_diagnostics
        result=system_diagnostics(self.db)
        self.assertEqual(result["division_count"],8)
        self.assertEqual(result["offer_count"],46)
        self.assertEqual(result["database_integrity"],"ok")


    def test_release_board_seeds_all_46_offers(self):
        from server import list_product_readiness
        data=list_product_readiness(self.db)
        self.assertEqual(data["total"],46)
        self.assertEqual(len({x["offer_id"] for x in data["items"]}),46)
    def test_release_state_requires_evidence(self):
        from server import update_product_readiness
        with self.assertRaises(ApiError):
            update_product_readiness("RA-001",{"state":"tested_local","evidence_ref":""},self.db)
        row=update_product_readiness("RA-001",{"state":"tested_local","evidence_ref":"local test report ref"},self.db)
        self.assertEqual(row["state"],"tested_local")
        self.assertFalse(row["evidence_is_independently_verified"])


    def test_document_intake_extracts_invoice_fields_for_review(self):
        from server import extract_document_fields
        result=extract_document_fields({"document_text":"Invoice Number: INV-12345\nInvoice Date: 2026-11-01\nVendor: Demo Supply\nTotal: $245.00"})
        self.assertEqual(result["document_type"],"invoice")
        self.assertEqual(result["fields"]["document_number"],"INV-12345")
        self.assertTrue(result["human_review_required"])
        self.assertFalse(result["saved_to_database"])
    def test_support_reply_uses_local_citations_and_is_not_sent(self):
        from server import create_knowledge_doc,draft_support_reply
        create_knowledge_doc({"title":"Warranty policy","division_id":"industry-solutions","source_ref":"internal/warranty-policy.md","content":"Warranty requests must be reviewed by a supervisor before a customer commitment is made."},self.db)
        result=draft_support_reply({"question":"How are warranty requests reviewed?"})
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["sent"])
        self.assertTrue(result["sources"])
        self.assertIn("supervisor",result["draft"])


    def test_revenue_quality_classifies_manual_inflows(self):
        from server import create_finance_entry,revenue_quality_summary
        create_finance_entry({"entry_type":"inflow","label":"Monthly service","category":"service","amount_cents":50000,"revenue_class":"recurring","collection_state":"collected_manual","source":"manual"},self.db)
        result=revenue_quality_summary(self.db)
        self.assertEqual(result["inflow_class_totals_cents"]["recurring"],50000)
        self.assertIn("not independently processor-verified",result["disclaimer"])
    def test_expense_review_groups_outflows(self):
        from server import create_finance_entry,expense_review_summary
        create_finance_entry({"entry_type":"outflow","label":"Hosting","category":"tools","amount_cents":10000},self.db)
        create_finance_entry({"entry_type":"outflow","label":"Phone","category":"tools","amount_cents":20000},self.db)
        result=expense_review_summary(self.db)
        self.assertEqual(result["recorded_outflows_cents"],30000)
        self.assertEqual(result["categories"][0]["share_of_recorded_outflows"],1.0)
    def test_runway_scenario_uses_manual_entries_and_cash_input(self):
        from server import create_finance_entry,runway_scenario
        create_finance_entry({"entry_type":"outflow","label":"Demo expenses","category":"operations","amount_cents":30000},self.db)
        result=runway_scenario({"available_cash_cents":90000,"period_days":30},self.db)
        self.assertEqual(result["estimated_monthly_net_burn_cents"],30000)
        self.assertEqual(result["runway_months_at_assumed_cash_and_burn"],3.0)


    def test_knowledge_evidence_link_is_recorded_and_retrieved(self):
        from server import create_knowledge_doc,create_knowledge_link,search_knowledge_graph
        first=create_knowledge_doc({"title":"Lead intake process","division_id":"revenue-automation","source_ref":"sop/lead-intake.md","content":"Assign every inbound lead to a named owner."},self.db)
        second=create_knowledge_doc({"title":"After-hours procedure","division_id":"revenue-automation","source_ref":"sop/after-hours.md","content":"After-hours enquiries are assigned to the on-call owner."},self.db)
        link=create_knowledge_link({"from_doc_id":first["id"],"to_doc_id":second["id"],"relation":"supports"},self.db)
        self.assertEqual(link["relation"],"supports")
        result=search_knowledge_graph("inbound lead owner",self.db)
        self.assertTrue(result["matches"])
        self.assertTrue(result["related"])
        self.assertEqual(result["edges"][0]["relation"],"supports")
    def test_knowledge_graph_rejects_self_link(self):
        from server import create_knowledge_doc,create_knowledge_link
        doc=create_knowledge_doc({"title":"One source","division_id":"enterprise-intelligence","source_ref":"one.md","content":"Some approved internal content."},self.db)
        with self.assertRaises(ApiError):
            create_knowledge_link({"from_doc_id":doc["id"],"to_doc_id":doc["id"],"relation":"related_to"},self.db)


    def test_local_backup_is_hash_and_sqlite_verified(self):
        from server import create_local_backup,verify_local_backup
        backup_dir=Path(self.tmp.name)/"backups"
        created=create_local_backup(self.db,backup_dir)
        result=verify_local_backup(created["filename"],self.db,backup_dir)
        self.assertTrue(result["valid"])
        self.assertEqual(result["database_integrity"],"ok")
        self.assertFalse(result["restore_performed"])
    def test_backup_tampering_is_detected(self):
        from server import create_local_backup,verify_local_backup
        backup_dir=Path(self.tmp.name)/"backups"
        created=create_local_backup(self.db,backup_dir)
        target=backup_dir/created["filename"]
        with target.open("ab") as stream:stream.write(b"tamper")
        result=verify_local_backup(created["filename"],self.db,backup_dir)
        self.assertFalse(result["valid"])
        self.assertFalse(result["checksum_match"])


    def test_workflow_definitions_and_full_lifecycle(self):
        from server import list_workflow_definitions,start_workflow,act_on_workflow_run
        defs=list_workflow_definitions(self.db)
        self.assertEqual(len(defs),6)
        run=start_workflow({"workflow_key":"lead_response_v1","context":{"summary":"Synthetic lead"}} ,self.db)
        self.assertEqual(run["status"],"active")
        for _ in range(len(run["steps"])):
            run=act_on_workflow_run(run["id"],{"action":"advance"},self.db)
        self.assertEqual(run["status"],"completed")
        self.assertFalse(run["external_actions_executed"])
    def test_workflow_can_be_blocked_and_resumed(self):
        from server import start_workflow,act_on_workflow_run
        run=start_workflow({"workflow_key":"dispatch_exception_v1"},self.db)
        blocked=act_on_workflow_run(run["id"],{"action":"block","note":"Await dispatcher review"},self.db)
        self.assertEqual(blocked["status"],"blocked")
        resumed=act_on_workflow_run(run["id"],{"action":"resume"},self.db)
        self.assertEqual(resumed["status"],"active")
    def test_workflow_rejects_sensitive_context_keys(self):
        from server import start_workflow
        with self.assertRaises(ApiError):
            start_workflow({"workflow_key":"support_reply_v1","context":{"password":"do-not-save"}},self.db)
    def test_workflow_cannot_advance_when_blocked(self):
        from server import start_workflow,act_on_workflow_run
        run=start_workflow({"workflow_key":"maintenance_request_v1"},self.db)
        act_on_workflow_run(run["id"],{"action":"block"},self.db)
        with self.assertRaises(ApiError):
            act_on_workflow_run(run["id"],{"action":"advance"},self.db)


    def test_digital_test_checkout_creates_pending_order_only(self):
        from digital_delivery import create_test_checkout,list_digital_entitlements
        order=create_test_checkout({"product_id":"IA-002"},self.db)
        self.assertEqual(order["status"],"pending")
        self.assertEqual(order["mode"],"test")
        self.assertFalse(order["payment_taken"])
        self.assertEqual(order["amount_cents"],900)
        self.assertEqual(list_digital_entitlements(self.db),[])
    def test_digital_signed_test_payment_grants_entitlement_and_token(self):
        from digital_delivery import create_test_checkout,simulate_test_payment,list_digital_entitlements
        order=create_test_checkout({"product_id":"IA-002"},self.db)
        result=simulate_test_payment(order["order_id"],self.db)
        self.assertTrue(result["entitlement_created"])
        self.assertTrue(result["download_token"])
        self.assertTrue(result["download_path"].startswith("/digital/download/"))
        self.assertEqual(list_digital_entitlements(self.db)[0]["status"],"active")
    def test_digital_invalid_signature_is_rejected(self):
        from digital_delivery import create_test_checkout,process_test_webhook,_signed_body
        order=create_test_checkout({"product_id":"WA-001"},self.db)
        event={"id":"evt_test_invalid","type":"payment_succeeded","mode":"test","livemode":False,
          "order_id":order["order_id"],"product_id":"WA-001","amount_cents":3700,"currency":"usd",
          "payment_reference":"test_payment_invalid","checkout_reference":"wrong_checkout"}
        raw,_=_signed_body(event,self.db)
        with self.assertRaises(ApiError):
            process_test_webhook(raw,"sha256="+"0"*64,self.db)
    def test_digital_authoritative_amount_mismatch_is_rejected(self):
        from digital_delivery import create_test_checkout,process_test_webhook,_signed_body
        order=create_test_checkout({"product_id":"WA-001"},self.db)
        event={"id":"evt_test_wrongamount","type":"payment_succeeded","mode":"test","livemode":False,
          "order_id":order["order_id"],"product_id":"WA-001","amount_cents":1,"currency":"usd",
          "payment_reference":"test_payment_wrongamount","checkout_reference":order["provider_reference"]}
        raw,sig=_signed_body(event,self.db)
        with self.assertRaises(ApiError):
            process_test_webhook(raw,sig,self.db)
    def test_digital_event_replay_is_idempotent(self):
        from digital_delivery import create_test_checkout,process_test_webhook,_signed_body,list_digital_entitlements
        order=create_test_checkout({"product_id":"MP-001"},self.db)
        event={"id":"evt_test_replay","type":"payment_succeeded","mode":"test","livemode":False,
          "order_id":order["order_id"],"product_id":"MP-001","amount_cents":2900,"currency":"usd",
          "payment_reference":"test_payment_replay","checkout_reference":order["provider_reference"]}
        raw,sig=_signed_body(event,self.db)
        first=process_test_webhook(raw,sig,self.db)
        second=process_test_webhook(raw,sig,self.db)
        self.assertTrue(first["entitlement_created"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(len(list_digital_entitlements(self.db)),1)
    def test_digital_wrong_checkout_reference_is_rejected(self):
        from digital_delivery import create_test_checkout,process_test_webhook,_signed_body
        order=create_test_checkout({"product_id":"HC-001"},self.db)
        event={"id":"evt_test_checkout_mismatch","type":"payment_succeeded","mode":"test","livemode":False,
          "order_id":order["order_id"],"product_id":"HC-001","amount_cents":2700,"currency":"usd",
          "payment_reference":"test_payment_mismatch","checkout_reference":"not-the-session"}
        raw,sig=_signed_body(event,self.db)
        with self.assertRaises(ApiError):
            process_test_webhook(raw,sig,self.db)
    def test_digital_refund_revokes_entitlement_and_download(self):
        from digital_delivery import create_test_checkout,simulate_test_payment,simulate_test_refund,consume_download_token
        order=create_test_checkout({"product_id":"HC-001"},self.db)
        paid=simulate_test_payment(order["order_id"],self.db)
        refunded=simulate_test_refund(order["order_id"],self.db)
        self.assertTrue(refunded["entitlement_revoked"])
        with self.assertRaises(ApiError):
            consume_download_token(paid["download_token"],self.db)
    def test_digital_asset_path_is_fixed_and_download_limit_enforced(self):
        import os
        from digital_delivery import create_test_checkout,simulate_test_payment,consume_download_token,ASSET_FILES
        assets=Path(self.tmp.name)/"private_assets";assets.mkdir()
        for pid,filename in ASSET_FILES.items():
            if pid=="IA-002":(assets/filename).write_bytes(b"%PDF-1.4 synthetic fixture")
        with mock.patch.dict(os.environ,{"GARCAR_DIGITAL_ASSET_DIR":str(assets)}):
            order=create_test_checkout({"product_id":"IA-002"},self.db)
            paid=simulate_test_payment(order["order_id"],self.db)
            path,meta=consume_download_token(paid["download_token"],self.db)
            self.assertEqual(path.name,ASSET_FILES["IA-002"])
            self.assertEqual(meta["remaining_downloads"],2)
            consume_download_token(paid["download_token"],self.db)
            consume_download_token(paid["download_token"],self.db)
            with self.assertRaises(ApiError):
                consume_download_token(paid["download_token"],self.db)
    def test_digital_missing_private_asset_blocks_download(self):
        from digital_delivery import create_test_checkout,simulate_test_payment,consume_download_token
        order=create_test_checkout({"product_id":"IA-002"},self.db)
        paid=simulate_test_payment(order["order_id"],self.db)
        with self.assertRaises(ApiError):
            consume_download_token(paid["download_token"],self.db)
    def test_digital_live_mode_event_is_rejected(self):
        from digital_delivery import create_test_checkout,process_test_webhook,_signed_body
        order=create_test_checkout({"product_id":"IA-003"},self.db)
        event={"id":"evt_test_liveflag","type":"payment_succeeded","mode":"test","livemode":True,
          "order_id":order["order_id"],"product_id":"IA-003","amount_cents":1900,"currency":"usd",
          "payment_reference":"test_payment_liveflag","checkout_reference":order["provider_reference"]}
        raw,sig=_signed_body(event,self.db)
        with self.assertRaises(ApiError):
            process_test_webhook(raw,sig,self.db)


    def test_download_bearer_token_is_redacted_from_access_log(self):
        import io
        from contextlib import redirect_stderr
        from server import Handler
        handler=object.__new__(Handler)
        handler.path="/digital/download/secret-bearer-token-value"
        output=io.StringIO()
        with redirect_stderr(output):
            handler.log_message("%s",handler.path)
        logged=output.getvalue()
        self.assertNotIn("secret-bearer-token-value",logged)
        self.assertIn("[TOKEN-REDACTED]",logged)

if __name__=="__main__":unittest.main()
