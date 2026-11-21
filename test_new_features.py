"""
Unit and Integration Tests for Features 1-5
===========================================
Tests:
  1. Feature 1: Legal Evidence & Claim Graph extraction & provenance
  2. Feature 2: Adaptive Retrieval Confidence Engine calibration & decision actions
  3. Feature 3: Interactive Human vs AI Moot Court 8-category scorecard & objection handler
  4. Feature 4: Automatic Case Timeline & Date Conflict detection
  5. Feature 5: Cross-Document Contradiction Detector & Claim pairing
"""

import unittest
from adaptive_retrieval_confidence import (
    evaluate_retrieval_confidence,
    calibrate_reranker_score,
    compute_lexical_overlap,
)
from legal_evidence_graph import heuristic_extract_graph, NODE_TYPES, RELATIONSHIP_TYPES
from case_timeline import (
    normalize_date_string,
    detect_date_conflicts,
    heuristic_extract_timeline,
)
from cross_document_contradictions import (
    heuristic_detect_contradictions,
    extract_key_claims_per_doc,
)
from moot_court import handle_courtroom_objection, generate_eight_category_scorecard


class TestAdaptiveRetrievalConfidence(unittest.TestCase):
    def test_reranker_calibration(self):
        # Raw logit > 0 should map to > 0.5
        self.assertGreater(calibrate_reranker_score(2.5), 0.5)
        # Raw logit < 0 should map to < 0.5
        self.assertLess(calibrate_reranker_score(-2.5), 0.5)
        # None should return default 0.5
        self.assertEqual(calibrate_reranker_score(None), 0.5)
        # Already normalized in [0, 1]
        self.assertEqual(calibrate_reranker_score(0.85), 0.85)

    def test_lexical_overlap(self):
        query = "dishonour of cheque under section 138"
        passages = [{"raw_text": "The cheque was returned by the bank with memo dishonour of cheque."}]
        overlap = compute_lexical_overlap(query, passages)
        self.assertGreater(overlap, 0.0)

    def test_high_confidence_action(self):
        query = "What is the limitation period for notice under Section 138?"
        passages = [
            {"score": 0.82, "source_file": "doc1.pdf", "raw_text": "Section 138 requires notice within 30 days of dishonour.", "rerank_score": 3.5},
            {"score": 0.78, "source_file": "doc2.pdf", "raw_text": "The limitation period is strictly 30 days under the proviso.", "rerank_score": 2.8},
        ]
        verification = {
            "citations": [
                {"verdict": "yes", "case_name": "Canbank"},
                {"verdict": "yes", "case_name": "Sakthivel"},
            ]
        }
        res = evaluate_retrieval_confidence(query, passages, top_score=0.82, verification=verification)
        self.assertEqual(res["level"], "high")
        self.assertEqual(res["recommended_action"], "answer")
        self.assertGreaterEqual(res["confidence"], 0.7)
        self.assertIn("dense_similarity", res["signals"])

    def test_low_confidence_refuse(self):
        query = "What are the rules for maritime admiralty arrest?"
        passages = [
            {"score": 0.38, "source_file": "unrelated.pdf", "raw_text": "Company registered office details."}
        ]
        res = evaluate_retrieval_confidence(query, passages, top_score=0.38)
        self.assertEqual(res["level"], "low")
        self.assertEqual(res["recommended_action"], "refuse")


class TestLegalEvidenceGraph(unittest.TestCase):
    def test_heuristic_graph_extraction(self):
        mock_records = [
            {
                "source_file": "Complaint.pdf",
                "page": 1,
                "raw_text": "In the High Court of Delhi. ABC Corp Versus XYZ Pvt Ltd. Complaint filed under Section 138 of Negotiable Instruments Act. PW-1 Inspector Sharma deposed on record.",
            },
            {
                "source_file": "Reply.pdf",
                "page": 2,
                "raw_text": "The accused asserts that cheque dishonour occurred without consideration. Order 39 Rule 1 applies to temporary injunctions.",
            }
        ]
        graph = heuristic_extract_graph(mock_records)
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertGreater(len(graph["nodes"]), 0)

        for n in graph["nodes"]:
            self.assertIn(n["type"], NODE_TYPES)
            self.assertTrue(n["source_document"])
            self.assertIn("confidence", n)
            self.assertIn("passage", n)

        for e in graph["edges"]:
            self.assertIn(e["relationship"], RELATIONSHIP_TYPES)
            self.assertTrue(e["source"])
            self.assertTrue(e["target"])


class TestTimelineAndDateConflicts(unittest.TestCase):
    def test_date_normalization(self):
        self.assertEqual(normalize_date_string("14/03/2022"), "2022-03-14")
        self.assertEqual(normalize_date_string("15th August 2021"), "2021-08-15")
        self.assertEqual(normalize_date_string("January 10, 2020"), "2020-01-10")

    def test_date_conflict_flagging(self):
        events = [
            {
                "title": "FIR Registered",
                "event_type": "fir",
                "date_normalized": "2022-04-10",
                "source_document": "Police_Report.pdf",
                "has_conflict": False,
            },
            {
                "title": "FIR Registered",
                "event_type": "fir",
                "date_normalized": "2022-04-15",
                "source_document": "Bail_Application.pdf",
                "has_conflict": False,
            }
        ]
        checked = detect_date_conflicts(events)
        self.assertTrue(checked[0]["has_conflict"])
        self.assertTrue(checked[1]["has_conflict"])
        self.assertIn("DATE CONFLICT", checked[0]["conflict_details"])

    def test_heuristic_timeline(self):
        records = [
            {
                "source_file": "Notice.pdf",
                "page": 1,
                "raw_text": "Legal notice dated 14/03/2022 was sent to the accused regarding dishonour of cheque dated 10/03/2022.",
            }
        ]
        tl = heuristic_extract_timeline(records)
        self.assertGreater(len(tl), 0)
        self.assertTrue(tl[0]["date_normalized"])


class TestCrossDocumentContradictions(unittest.TestCase):
    def test_amount_contradiction_detection(self):
        records = [
            {
                "source_file": "DocA_Agreement.pdf",
                "page": 1,
                "raw_text": "The loan disbursed was Rs. 50,00,000 to the borrower.",
            },
            {
                "source_file": "DocB_Statement.pdf",
                "page": 2,
                "raw_text": "The total amount received was only Rs. 35,00,000 as consideration.",
            }
        ]
        contras = heuristic_detect_contradictions(records)
        self.assertGreater(len(contras), 0)
        c = contras[0]
        self.assertIn(c["status"], {"confirmed", "possible"})
        self.assertTrue(c["claim_a"]["source_document"])
        self.assertTrue(c["claim_b"]["source_document"])
        self.assertNotEqual(c["claim_a"]["source_document"], c["claim_b"]["source_document"])

    def test_notice_service_contradiction(self):
        records = [
            {
                "source_file": "Complainant_Affidavit.pdf",
                "page": 1,
                "raw_text": "The statutory notice was duly served upon the accused on 15-Jan.",
            },
            {
                "source_file": "Accused_Reply.pdf",
                "page": 1,
                "raw_text": "The notice was returned unserved and never received by the defense.",
            }
        ]
        contras = heuristic_detect_contradictions(records)
        self.assertGreater(len(contras), 0)
        self.assertEqual(contras[0]["status"], "confirmed")


class TestMootCourtFeatures(unittest.TestCase):
    def test_courtroom_objection_handling(self):
        obj = handle_courtroom_objection(
            dispute="Director liability under Section 141 NI Act",
            objecting_party="Senior Counsel for Respondent",
            ground="Leading question / speculative pleading",
            target_statement="The director had full personal knowledge of daily transactions.",
        )
        self.assertIn("ruling", obj)
        self.assertIn(obj["ruling"], {"SUSTAINED", "OVERRULED", "NOTED"})
        self.assertTrue(obj["bench_response"])

    def test_scorecard_categories(self):
        sc = generate_eight_category_scorecard(
            dispute="Cheque bounce liability",
            human_argument="May it please Your Lordship, Section 138 creates a strict liability once signature is admitted.",
            opponent_argument="May it please the Bench, the presumption under Section 139 is rebuttable by preponderance of probabilities.",
            judicial_order="Petition Allowed. The accused failed to raise a probable defense.",
            user_role="petitioner",
        )
        self.assertIn("categories", sc)
        self.assertIn("overall_score", sc)
        expected_cats = {
            "legal_reasoning", "evidence_grounding", "precedent_usage",
            "statutory_accuracy", "counterargument_handling",
            "argument_structure", "responsiveness"
        }
        for cat in expected_cats:
            self.assertIn(cat, sc["categories"])
            self.assertIn("score", sc["categories"][cat])
            self.assertIn("feedback", sc["categories"][cat])


if __name__ == "__main__":
    unittest.main()
