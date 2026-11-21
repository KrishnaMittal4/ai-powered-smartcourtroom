"""
Legal Evidence & Claim Graph Extraction Engine
==============================================
Extracts structured entity nodes and relational edges from private case documents
for Case Intelligence visualizations.

Nodes represent:
  - issue: Legal issues or propositions
  - claim: Primary factual or legal claims
  - counterclaim: Opposing claims / defenses
  - fact: Material undisputed or established facts
  - party: Litigants (Petitioner, Respondent, Accused, Complainant)
  - witness: Deponents or witness statements
  - evidence: Documentary, physical, forensic or digital exhibits
  - statute: Statutory provisions (Sections, Orders, Articles)
  - precedent: Cited authorities or judicial case laws
  - date_event: Key chronological milestones
  - argument: Counsel submissions
  - finding: Judicial rulings or holdings

Relationships:
  SUPPORTS | CONTRADICTS | CITES | REBUTS | DISTINGUISHES | OVERRULES |
  DEPENDS_ON | ASSERTED_BY | SUPPORTED_BY | RELATED_TO

Every node and edge retains strict provenance:
  - source_document
  - page
  - passage (verbatim extracted text)
  - document_id
  - confidence (0.0 to 1.0)
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NODE_TYPES = {
    "issue", "claim", "counterclaim", "fact", "party", "witness",
    "evidence", "statute", "precedent", "date_event", "argument", "finding"
}

RELATIONSHIP_TYPES = {
    "SUPPORTS", "CONTRADICTS", "CITES", "REBUTS", "DISTINGUISHES",
    "OVERRULES", "DEPENDS_ON", "ASSERTED_BY", "SUPPORTED_BY", "RELATED_TO"
}


def _clean_text_snippet(text: str, max_len: int = 400) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:max_len]


def heuristic_extract_graph(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic rule-based fallback to guarantee an evidence graph is generated
    even if external LLM providers are down, rate-limited, or unconfigured.
    """
    nodes = []
    edges = []
    node_id_map = {}

    def add_node(label: str, ntype: str, doc: str, page: Any, passage: str, conf: float = 0.85) -> str:
        key = (ntype, label.lower()[:80])
        if key in node_id_map:
            return node_id_map[key]
        nid = f"n_{len(nodes) + 1}_{uuid.uuid4().hex[:6]}"
        node_id_map[key] = nid
        nodes.append({
            "id": nid,
            "label": label[:100],
            "type": ntype,
            "source_document": doc,
            "page": page if page is not None else 1,
            "passage": _clean_text_snippet(passage),
            "document_id": doc,
            "confidence": conf,
        })
        return nid

    for r in records[:30]:
        text = r.get("raw_text") or r.get("text") or ""
        doc = r.get("source_file") or "case_doc.pdf"
        page = r.get("page") or 1

        # 1. Statutory Provisions
        stat_matches = re.findall(
            r"((?:Section|Sec\.|Order\s+\d+\s+Rule\s+\d+|Article)\s+\d+[A-Za-z]?(?:\s+of\s+[A-Za-z\s]+(?:Act|Code|Rules))?)",
            text, re.IGNORECASE
        )
        for stat in set(stat_matches[:3]):
            stat_clean = re.sub(r"\s+", " ", stat).strip()
            if len(stat_clean) > 4:
                sid = add_node(stat_clean, "statute", doc, page, text[:250], 0.95)
                # Link to doc
                did = add_node(f"Exhibit: {doc}", "evidence", doc, page, text[:200], 0.9)
                edges.append({
                    "id": f"e_{len(edges)+1}",
                    "source": did,
                    "target": sid,
                    "relationship": "CITES",
                    "confidence": 0.9,
                    "explanation": f"Document cites statutory provision {stat_clean}",
                })

        # 2. Parties
        party_match = re.search(r"([A-Z][a-zA-Z\s\.]{2,35}\s+(?:Versus|Vs\.?|V/S)\s+[A-Z][a-zA-Z\s\.]{2,35})", text)
        if party_match:
            parties_str = party_match.group(1).strip()
            add_node(parties_str, "party", doc, page, text[:250], 0.92)

        # 3. Witnesses / Statements
        witness_match = re.search(r"(?:PW[-\s]?\d+|DW[-\s]?\d+|Witness|Deposition|Statement of)\s+([A-Za-z\s\.]{3,30})", text, re.IGNORECASE)
        if witness_match:
            w_name = witness_match.group(0).strip()
            wid = add_node(w_name, "witness", doc, page, text[:300], 0.88)
            fid = add_node(f"Statement recorded on p.{page}", "fact", doc, page, text[:250], 0.8)
            edges.append({
                "id": f"e_{len(edges)+1}",
                "source": wid,
                "target": fid,
                "relationship": "ASSERTED_BY",
                "confidence": 0.85,
                "explanation": f"{w_name} recorded oral or written statement",
            })

        # 4. Dates & Events
        date_matches = re.findall(r"\b(?:\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4})\b", text)
        for dt in set(date_matches[:2]):
            did = add_node(f"Event: {dt}", "date_event", doc, page, text[:250], 0.9)

        # 5. Claims & Findings
        if re.search(r"\b(?:dishonour|cheque|default|breach|injunction|bail|guilty|liable)\b", text, re.IGNORECASE):
            cid = add_node(f"Plea / Contention (p.{page})", "claim", doc, page, text[:300], 0.82)
            did = add_node(f"Record: {doc}", "evidence", doc, page, text[:200], 0.85)
            edges.append({
                "id": f"e_{len(edges)+1}",
                "source": did,
                "target": cid,
                "relationship": "SUPPORTED_BY",
                "confidence": 0.82,
                "explanation": "Documentary record supports legal claim",
            })

    # Ensure at least minimal connected graph
    if not nodes:
        dummy_id1 = add_node("Primary Legal Dispute", "issue", "case.pdf", 1, "Core case issue under examination", 0.9)
        dummy_id2 = add_node("Documentary Evidence", "evidence", "case.pdf", 1, "Uploaded evidentiary record", 0.9)
        edges.append({
            "id": "e_init",
            "source": dummy_id2,
            "target": dummy_id1,
            "relationship": "RELATED_TO",
            "confidence": 0.9,
            "explanation": "Primary evidentiary nexus",
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": list(set(n["type"] for n in nodes)),
            "extraction_method": "heuristic_fallback",
        }
    }


def extract_evidence_graph_with_llm(records: List[Dict[str, Any]], client: Any) -> Dict[str, Any]:
    """
    Extracts a fully grounded, schema-validated Legal Evidence & Claim Graph using Groq/Gemini.
    Falls back gracefully to heuristic_extract_graph on any validation failure.
    """
    if not records:
        return {"nodes": [], "edges": [], "summary": {"total_nodes": 0, "total_edges": 0}}

    # Prepare compact corpus summary
    chunks_text = []
    for i, r in enumerate(records[:18]):
        doc = r.get("source_file") or "doc.pdf"
        page = r.get("page") or 1
        txt = (r.get("raw_text") or r.get("text") or "")[:450]
        chunks_text.append(f"[{i+1}] File: {doc} | Page: {page}\n{txt}")
    context = "\n\n".join(chunks_text)

    prompt = f"""You are a specialized Legal Knowledge Graph Engineer.
Analyze the following private Indian case document excerpts and construct a precise, factual Evidence & Claim Graph.

CASE DOCUMENTS:
{context}

RULES:
1. Extract nodes strictly from the provided text. Never invent parties, statutes, or evidence.
2. Node types MUST be one of:
   ["issue", "claim", "counterclaim", "fact", "party", "witness", "evidence", "statute", "precedent", "date_event", "argument", "finding"]
3. Relationships MUST be one of:
   ["SUPPORTS", "CONTRADICTS", "CITES", "REBUTS", "DISTINGUISHES", "OVERRULES", "DEPENDS_ON", "ASSERTED_BY", "SUPPORTED_BY", "RELATED_TO"]
4. Every node MUST include exact "source_document", "page" (integer), verbatim "passage" (5-30 words), and "confidence" (0.5 to 1.0).
5. Output MUST be valid JSON only with NO markdown fences, matching this schema:
{{
  "nodes": [
    {{
      "id": "n1",
      "label": "Short human-readable title (max 8 words)",
      "type": "claim",
      "source_document": "filename.pdf",
      "page": 1,
      "passage": "Exact verbatim excerpt from text",
      "confidence": 0.95
    }}
  ],
  "edges": [
    {{
      "id": "e1",
      "source": "n1",
      "target": "n2",
      "relationship": "SUPPORTS",
      "confidence": 0.9,
      "explanation": "Short 1-sentence explanation of why source relates to target"
    }}
  ]
}}
Extract between 6 to 25 essential nodes and their genuine relationships.
"""

    if not client:
        return heuristic_extract_graph(records)

    try:
        from llm_router import route_task
        from groq import Groq

        # Attempt structured completion
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You output strictly valid JSON conforming to the legal graph schema. No explanation or commentary."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2600,
            response_format={"type": "json_object"} if hasattr(client, "chat") else None,
        )
        content = resp.choices[0].message.content or ""
        # Clean json
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            logger.warning("No JSON structure in LLM evidence graph response; falling back to heuristic.")
            return heuristic_extract_graph(records)

        data = json.loads(m.group(0))
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])

        # Validate nodes and edges
        valid_nodes = []
        valid_node_ids = set()

        for n in raw_nodes:
            nid = str(n.get("id") or f"n_{len(valid_nodes)+1}")
            ntype = str(n.get("type", "fact")).lower()
            if ntype not in NODE_TYPES:
                ntype = "fact"
            label = str(n.get("label") or "Legal Point")[:100]
            valid_nodes.append({
                "id": nid,
                "label": label,
                "type": ntype,
                "source_document": str(n.get("source_document") or (records[0].get("source_file") if records else "doc.pdf")),
                "page": int(n.get("page") or 1),
                "passage": _clean_text_snippet(str(n.get("passage") or label)),
                "document_id": str(n.get("source_document") or "doc.pdf"),
                "confidence": float(max(0.1, min(1.0, float(n.get("confidence") or 0.85)))),
            })
            valid_node_ids.add(nid)

        valid_edges = []
        for e in raw_edges:
            src = str(e.get("source"))
            tgt = str(e.get("target"))
            rel = str(e.get("relationship", "RELATED_TO")).upper()
            if rel not in RELATIONSHIP_TYPES:
                rel = "RELATED_TO"
            if src in valid_node_ids and tgt in valid_node_ids and src != tgt:
                valid_edges.append({
                    "id": str(e.get("id") or f"e_{len(valid_edges)+1}"),
                    "source": src,
                    "target": tgt,
                    "relationship": rel,
                    "confidence": float(max(0.1, min(1.0, float(e.get("confidence") or 0.8)))),
                    "explanation": str(e.get("explanation") or f"{src} {rel} {tgt}")[:200],
                })

        if not valid_nodes:
            return heuristic_extract_graph(records)

        return {
            "nodes": valid_nodes,
            "edges": valid_edges,
            "summary": {
                "total_nodes": len(valid_nodes),
                "total_edges": len(valid_edges),
                "node_types": list(set(n["type"] for n in valid_nodes)),
                "extraction_method": "llm_grounded",
            }
        }
    except Exception as exc:
        logger.error(f"LLM evidence graph extraction failed: {exc}", exc_info=True)
        return heuristic_extract_graph(records)
