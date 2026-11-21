"""
Cross-Document Contradiction Detector
====================================
Identifies factual contradictions, evidentiary disputes, and inconsistent assertions
across multiple uploaded private case documents.

Contradiction Categories:
  - dates / times: e.g. occurrence at 8 PM vs 11 PM
  - locations: e.g. location A vs location B
  - amounts / sums: e.g. loan of Rs. 5,00,000 vs Rs. 3,50,000
  - identities / parties: e.g. individual signatory vs firm transaction
  - witness statements: e.g. witness A denies presence vs witness B claims presence
  - document assertions: e.g. notice served vs notice returned unserved

Levels:
  - "confirmed": Direct, irreconcilable factual clash between documents
  - "possible": Ambiguous or varying assertions requiring judicial clarification
  - "not_contradiction": Normal differences in emphasis or complementary perspectives

Every contradiction record preserves:
  - claim_a: {source_document, page, passage}
  - claim_b: {source_document, page, passage}
  - status: "confirmed" | "possible"
  - category: str
  - confidence: float
  - explanation: str
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_key_claims_per_doc(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Groups records and extracts material factual assertions per source document."""
    by_doc: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        doc = r.get("source_file") or "case_doc.pdf"
        if doc not in by_doc:
            by_doc[doc] = []
        by_doc[doc].append(r)
    return by_doc


def heuristic_detect_contradictions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rule-based cross-document discrepancy scanner."""
    by_doc = extract_key_claims_per_doc(records)
    doc_names = list(by_doc.keys())
    if len(doc_names) < 2:
        return []

    contradictions = []

    # Check for monetary amounts disparity across documents
    amount_pattern = r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)"
    doc_amounts = {}
    for doc, recs in by_doc.items():
        doc_amounts[doc] = []
        for r in recs:
            txt = r.get("raw_text") or r.get("text") or ""
            matches = re.findall(amount_pattern, txt)
            for m in matches:
                clean_num = m.replace(",", "")
                try:
                    val = float(clean_num)
                    if val > 1000:
                        doc_amounts[doc].append({
                            "val": val,
                            "raw": m,
                            "page": r.get("page", 1),
                            "passage": txt[:250],
                        })
                except ValueError:
                    pass

    # Compare amounts between distinct documents
    for i in range(len(doc_names)):
        for j in range(i + 1, len(doc_names)):
            doc_a, doc_b = doc_names[i], doc_names[j]
            amts_a = doc_amounts.get(doc_a, [])
            amts_b = doc_amounts.get(doc_b, [])
            if amts_a and amts_b:
                vals_a = set(a["val"] for a in amts_a)
                vals_b = set(b["val"] for b in amts_b)
                # If there are disjoint large numbers cited as the transaction value
                diff = vals_a.symmetric_difference(vals_b)
                if len(diff) >= 2 and not (vals_a & vals_b):
                    item_a = amts_a[0]
                    item_b = amts_b[0]
                    contradictions.append({
                        "id": f"contra_{len(contradictions)+1}",
                        "category": "amounts",
                        "status": "possible",
                        "confidence": 0.82,
                        "explanation": f"Discrepancy in monetary figures cited in {doc_a} (Rs. {item_a['raw']}) vs {doc_b} (Rs. {item_b['raw']}).",
                        "claim_a": {
                            "source_document": doc_a,
                            "page": item_a["page"],
                            "passage": item_a["passage"],
                        },
                        "claim_b": {
                            "source_document": doc_b,
                            "page": item_b["page"],
                            "passage": item_b["passage"],
                        },
                    })

    # Check for Service of Notice vs Non-receipt claims
    doc_service_claims = {}
    for doc, recs in by_doc.items():
        for r in recs:
            txt = (r.get("raw_text") or r.get("text") or "").lower()
            if re.search(r"\b(?:not\s+served|unserved|never\s+received|returned\s+with\s+postal\s+endorsement|refused|non-receipt)\b", txt):
                doc_service_claims[doc] = {"served": False, "page": r.get("page", 1), "passage": (r.get("raw_text") or "")[:250]}
                break
            elif re.search(r"\b(?:duly\s+served|served\s+upon|delivered\s+to|received\s+by)\b", txt):
                doc_service_claims[doc] = {"served": True, "page": r.get("page", 1), "passage": (r.get("raw_text") or "")[:250]}
                break

    service_docs = list(doc_service_claims.keys())
    for i in range(len(service_docs)):
        for j in range(i + 1, len(service_docs)):
            da, db = service_docs[i], service_docs[j]
            if doc_service_claims[da]["served"] != doc_service_claims[db]["served"]:
                contradictions.append({
                    "id": f"contra_{len(contradictions)+1}",
                    "category": "document_assertions",
                    "status": "confirmed",
                    "confidence": 0.92,
                    "explanation": f"Direct dispute regarding notice delivery: {da} asserts receipt whereas {db} disputes service.",
                    "claim_a": {
                        "source_document": da,
                        "page": doc_service_claims[da]["page"],
                        "passage": doc_service_claims[da]["passage"],
                    },
                    "claim_b": {
                        "source_document": db,
                        "page": doc_service_claims[db]["page"],
                        "passage": doc_service_claims[db]["passage"],
                    },
                })

    return contradictions


def detect_cross_document_contradictions(records: List[Dict[str, Any]], client: Any) -> Dict[str, Any]:
    """
    Orchestrates candidate pairing across documents followed by structured LLM NLI evaluation.
    Falls back gracefully to heuristic checks.
    """
    if not records:
        return {"contradictions": [], "summary": {"total": 0, "confirmed": 0, "possible": 0}}

    heuristic_results = heuristic_detect_contradictions(records)

    by_doc = extract_key_claims_per_doc(records)
    if len(by_doc) < 2:
        return {
            "contradictions": [],
            "summary": {
                "total": 0,
                "confirmed": 0,
                "possible": 0,
                "note": "Cross-document contradiction analysis requires at least two distinct documents.",
            }
        }

    if not client:
        return {
            "contradictions": heuristic_results,
            "summary": {
                "total": len(heuristic_results),
                "confirmed": sum(1 for c in heuristic_results if c.get("status") == "confirmed"),
                "possible": sum(1 for c in heuristic_results if c.get("status") == "possible"),
                "method": "heuristic",
            }
        }

    # Prepare cross-document excerpts
    snippets = []
    for doc, recs in list(by_doc.items())[:4]:
        doc_text = " ".join((r.get("raw_text") or r.get("text") or "")[:350] for r in recs[:3])
        snippets.append(f"DOCUMENT: {doc}\n{doc_text[:1200]}")
    context = "\n\n---\n\n".join(snippets)

    prompt = f"""You are a Cross-Document Legal Contradiction & Inconsistency Detector.
Analyze the following excerpts from distinct case documents and detect genuine factual contradictions.

CASE DOCUMENTS:
{context}

RULES:
1. Only detect contradictions where two documents present mutually incompatible statements about:
   - dates / times of events
   - monetary amounts or consideration
   - vehicle / object descriptions
   - witness statements & presence
   - service of statutory notice / acknowledgment
   - authority or signing capacity
2. Do NOT mark ordinary complementary facts or procedural stages as contradictions.
3. Status MUST be "confirmed" (direct irreconcilable clash) or "possible" (divergent account).
4. Output MUST be valid JSON only with NO markdown fences:
{{
  "contradictions": [
    {{
      "category": "dates",
      "status": "confirmed",
      "confidence": 0.95,
      "explanation": "Document A states transaction occurred on 12-May whereas Document B claims 18-May.",
      "claim_a": {{
        "source_document": "Notice.pdf",
        "page": 1,
        "passage": "Exact quote from document A"
      }},
      "claim_b": {{
        "source_document": "Reply.pdf",
        "page": 2,
        "passage": "Exact quote from document B"
      }}
    }}
  ]
}}
"""
    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You output JSON only. Strictly grounded; no false contradictions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return {
                "contradictions": heuristic_results,
                "summary": {"total": len(heuristic_results), "confirmed": 0, "possible": len(heuristic_results), "method": "heuristic"}
            }

        data = json.loads(m.group(0))
        raw = data.get("contradictions", [])
        verified = []
        for i, c in enumerate(raw):
            status = c.get("status")
            if status not in {"confirmed", "possible"}:
                continue
            verified.append({
                "id": f"contra_{i+1}",
                "category": str(c.get("category", "factual_claims")),
                "status": status,
                "confidence": float(max(0.5, min(1.0, float(c.get("confidence") or 0.85)))),
                "explanation": str(c.get("explanation") or "Factual discrepancy identified between documents.")[:300],
                "claim_a": {
                    "source_document": str(c.get("claim_a", {}).get("source_document") or "doc_a.pdf"),
                    "page": int(c.get("claim_a", {}).get("page") or 1),
                    "passage": str(c.get("claim_a", {}).get("passage") or "")[:300],
                },
                "claim_b": {
                    "source_document": str(c.get("claim_b", {}).get("source_document") or "doc_b.pdf"),
                    "page": int(c.get("claim_b", {}).get("page") or 1),
                    "passage": str(c.get("claim_b", {}).get("passage") or "")[:300],
                },
            })

        # Combine with any heuristic confirmed entries
        final_list = verified if verified else heuristic_results
        return {
            "contradictions": final_list,
            "summary": {
                "total": len(final_list),
                "confirmed": sum(1 for x in final_list if x.get("status") == "confirmed"),
                "possible": sum(1 for x in final_list if x.get("status") == "possible"),
                "method": "llm_grounded" if verified else "heuristic",
            }
        }
    except Exception as exc:
        logger.error(f"LLM contradiction detection failed: {exc}", exc_info=True)
        return {
            "contradictions": heuristic_results,
            "summary": {"total": len(heuristic_results), "confirmed": 0, "possible": len(heuristic_results), "method": "heuristic"}
        }
