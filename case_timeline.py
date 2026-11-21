"""
Automatic Case Timeline Engine with Date Conflict Detection
============================================================
Chronologically sorts legally relevant events extracted from private case documents.
Detects:
  - Incident, Complaint, FIR, Arrest, Notice, Investigation, Evidence collection,
    Chargesheet, Hearing, Order, Judgment, Appeal, Deadline.

Provenance:
  {
    "date": str,
    "date_normalized": str (YYYY-MM-DD or YYYY-MM),
    "title": str,
    "event_type": str,
    "description": str,
    "source_document": str,
    "page": int,
    "source_text": str,
    "confidence": float,
    "has_conflict": bool,
    "conflict_details": Optional[str]
  }

Identifies DATE CONFLICT when multiple documents report conflicting dates for the same
milestone (e.g. Complaint dated 12-Jan vs 15-Jan).
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "incident", "complaint", "fir", "arrest", "notice", "investigation",
    "evidence_collection", "chargesheet", "hearing", "order", "judgment",
    "appeal", "deadline", "other"
}

MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}


def normalize_date_string(raw: str) -> Optional[str]:
    """Attempts to standardize varied Indian legal date formats into YYYY-MM-DD."""
    if not raw:
        return None
    cleaned = raw.strip().lower().rstrip(".,;")

    # 1. DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})$", cleaned)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mth <= 12:
            return f"{y:04d}-{mth:02d}-{d:02d}"

    # 2. DDth Month YYYY (e.g. 15th August 2021, 4 May 2022)
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)[\s,]+(\d{4})", cleaned)
    if m:
        d = int(m.group(1))
        mth_str = m.group(2)
        y = int(m.group(3))
        mth_num = MONTH_MAP.get(mth_str[:3])
        if mth_num and 1 <= d <= 31:
            return f"{y:04d}-{mth_num}-{d:02d}"

    # 3. Month DD, YYYY
    m = re.search(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[\s,]+(\d{4})", cleaned)
    if m:
        mth_str = m.group(1)
        d = int(m.group(2))
        y = int(m.group(3))
        mth_num = MONTH_MAP.get(mth_str[:3])
        if mth_num and 1 <= d <= 31:
            return f"{y:04d}-{mth_num}-{d:02d}"

    # 4. YYYY only
    m = re.match(r"^(\d{4})$", cleaned)
    if m:
        return f"{m.group(1)}-01-01"

    return None


def detect_date_conflicts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups events by type/normalized milestone and flags discrepancies in dates.
    Does NOT silently merge; instead, surfaces DATE CONFLICT flags.
    """
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        etype = ev.get("event_type", "other")
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(ev)

    for etype, group in by_type.items():
        if etype in {"other", "hearing"}:
            continue  # Multiple hearings on different dates are normal
        dates = set(e.get("date_normalized") for e in group if e.get("date_normalized"))
        if len(dates) > 1 and len(group) >= 2:
            # Conflict detected!
            conflict_msg = f"DATE CONFLICT: Multiple sources cite different dates ({', '.join(sorted(dates))}) for {etype.replace('_', ' ').title()}."
            for e in group:
                e["has_conflict"] = True
                e["conflict_details"] = conflict_msg

    return events


def heuristic_extract_timeline(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rule-based extraction of legal milestones and dates."""
    events = []
    seen = set()

    patterns = [
        (r"(?:dishonou?r(?:ed)?|cheque\s+returned)\s+(?:on|dated)\s+([\w\s,/-]+?\d{4})", "incident", "Cheque Dishonour"),
        (r"(?:statutory\s+notice|legal\s+notice|demand\s+notice)\s+(?:issued|dated|sent)\s+([\w\s,/-]+?\d{4})", "notice", "Legal Demand Notice"),
        (r"(?:complaint|petition)\s+(?:filed|instituted)\s+(?:on|dated)\s+([\w\s,/-]+?\d{4})", "complaint", "Complaint Filed"),
        (r"(?:fir|first\s+information\s+report)\s+(?:no\.?\s*[\w/]+\s+)?(?:registered|dated)\s+([\w\s,/-]+?\d{4})", "fir", "FIR Registered"),
        (r"(?:arrested|taken\s+into\s+custody)\s+(?:on|dated)\s+([\w\s,/-]+?\d{4})", "arrest", "Accused Arrested"),
        (r"(?:chargesheet|final\s+report)\s+(?:filed|submitted)\s+(?:on|dated)\s+([\w\s,/-]+?\d{4})", "chargesheet", "Chargesheet Filed"),
        (r"(?:order|injunction|judgment|decree)\s+(?:passed|pronounced|dated)\s+([\w\s,/-]+?\d{4})", "order", "Judicial Order / Judgment"),
    ]

    for r in records:
        txt = r.get("raw_text") or r.get("text") or ""
        doc = r.get("source_file") or "case_doc.pdf"
        page = r.get("page") or 1

        for regex, etype, title in patterns:
            for match in re.finditer(regex, txt, re.IGNORECASE):
                raw_dt = match.group(1).strip()[:30]
                norm_dt = normalize_date_string(raw_dt)
                if not norm_dt:
                    continue
                key = (etype, norm_dt, doc)
                if key not in seen:
                    seen.add(key)
                    snippet = txt[max(0, match.start() - 40): min(len(txt), match.end() + 100)]
                    events.append({
                        "id": f"ev_{len(events)+1}",
                        "date": raw_dt,
                        "date_normalized": norm_dt,
                        "title": title,
                        "event_type": etype,
                        "description": re.sub(r"\s+", " ", snippet).strip(),
                        "source_document": doc,
                        "page": int(page),
                        "source_text": re.sub(r"\s+", " ", snippet).strip(),
                        "confidence": 0.88,
                        "has_conflict": False,
                        "conflict_details": None,
                    })

    # Sort chronologically by normalized date
    events.sort(key=lambda x: x.get("date_normalized") or "9999-99-99")
    return detect_date_conflicts(events)


def extract_timeline_with_llm(records: List[Dict[str, Any]], client: Any) -> Dict[str, Any]:
    """Extracts high-fidelity chronological events from case documents."""
    if not records:
        return {"events": [], "conflict_count": 0}

    heuristic_events = heuristic_extract_timeline(records)

    if not client:
        return {
            "events": heuristic_events,
            "conflict_count": sum(1 for e in heuristic_events if e.get("has_conflict")),
            "method": "heuristic",
        }

    # Prepare excerpts
    snippets = []
    for i, r in enumerate(records[:15]):
        txt = (r.get("raw_text") or r.get("text") or "")[:400]
        doc = r.get("source_file") or "doc.pdf"
        page = r.get("page") or 1
        snippets.append(f"[{i+1}] {doc} (p.{page}): {txt}")
    context = "\n\n".join(snippets)

    prompt = f"""You are a Legal Chronology & Case Timeline Specialist.
Analyze the following private case excerpts and extract all factual dates and procedural milestones.

CASE EXCERPTS:
{context}

RULES:
1. Extract milestones such as Incident, Notice, Complaint, FIR, Arrest, Investigation, Chargesheet, Hearing, Order, Judgment, Deadline.
2. For each event, provide exact or standard date (e.g. "12 Jan 2023"), normalized date (YYYY-MM-DD), event_type, title, description, source_document, page number, and source_text.
3. If two documents disagree on a date for the SAME milestone, set "has_conflict": true and provide "conflict_details".
4. Output MUST be valid JSON only with NO markdown fences:
{{
  "events": [
    {{
      "date": "14 March 2022",
      "date_normalized": "2022-03-14",
      "title": "Dishonour of Cheque No. 44102",
      "event_type": "incident",
      "description": "Cheque returned by bank with endorsement 'Funds Insufficient'.",
      "source_document": "Notice.pdf",
      "page": 1,
      "source_text": "Cheque dated 10-03-2022 was presented and dishonoured on 14-03-2022",
      "confidence": 0.95,
      "has_conflict": false,
      "conflict_details": null
    }}
  ]
}}
"""
    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You output JSON only. Do not hallucinate dates or events."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return {"events": heuristic_events, "conflict_count": sum(1 for e in heuristic_events if e.get("has_conflict")), "method": "heuristic"}

        data = json.loads(m.group(0))
        raw_events = data.get("events", [])
        clean_events = []
        for i, ev in enumerate(raw_events):
            norm = ev.get("date_normalized") or normalize_date_string(ev.get("date", ""))
            clean_events.append({
                "id": f"ev_{i+1}",
                "date": str(ev.get("date") or "Unknown Date"),
                "date_normalized": norm or "9999-99-99",
                "title": str(ev.get("title") or "Case Event")[:100],
                "event_type": str(ev.get("event_type", "other")).lower(),
                "description": str(ev.get("description") or "")[:300],
                "source_document": str(ev.get("source_document") or (records[0].get("source_file") if records else "doc.pdf")),
                "page": int(ev.get("page") or 1),
                "source_text": str(ev.get("source_text") or "")[:300],
                "confidence": float(max(0.1, min(1.0, float(ev.get("confidence") or 0.85)))),
                "has_conflict": bool(ev.get("has_conflict", False)),
                "conflict_details": ev.get("conflict_details"),
            })

        # Merge with any detected conflicts
        clean_events.sort(key=lambda x: x.get("date_normalized") or "9999-99-99")
        final_events = detect_date_conflicts(clean_events) if clean_events else heuristic_events
        return {
            "events": final_events,
            "conflict_count": sum(1 for e in final_events if e.get("has_conflict")),
            "method": "llm_grounded",
        }
    except Exception as exc:
        logger.error(f"LLM timeline extraction failed: {exc}", exc_info=True)
        return {"events": heuristic_events, "conflict_count": sum(1 for e in heuristic_events if e.get("has_conflict")), "method": "heuristic"}
