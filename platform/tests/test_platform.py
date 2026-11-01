import tempfile
import unittest
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

if __name__=="__main__":unittest.main()
