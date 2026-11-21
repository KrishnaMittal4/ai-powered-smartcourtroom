"""
Statutory Limitation & Procedural Timeline Checker for Indian Law
================================================================
Calculates limitation windows, statutory notice cure periods, and
filing deadlines from case facts or document dates.
"""

from datetime import datetime, timedelta
import re

LIMITATION_RULES = {
    "ni_act_138": {
        "title": "Negotiable Instruments Act (Section 138 / 142)",
        "notice_demand_days": 30,       # statutory notice within 30 days of dishonour memo
        "cure_period_days": 15,         # accused given 15 days to pay from receipt
        "complaint_limitation_days": 30 # criminal complaint within 1 month (30 days) of cause of action
    },
    "consumer_protection": {
        "title": "Consumer Protection Act, 2019 (Section 69)",
        "limitation_years": 2           # within 2 years from date on which cause of action arose
    },
    "criminal_quashing": {
        "title": "Criminal Procedure Code / BNSS",
        "guideline": "Prompt petition advised; unexplained delay can be grounds for dismissal."
    },
    "contract_recovery": {
        "title": "Limitation Act, 1963 (Articles 14, 55)",
        "limitation_years": 3           # 3 years from date of breach / refusal
    }
}

def parse_date(date_str: str):
    """Attempts to parse common Indian date formats (DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY)."""
    if not date_str:
        return None
    cleaned = date_str.strip()
    formats = ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None

def check_ni_act_timeline(memo_date_str: str, notice_served_date_str: str, complaint_date_str: str = None):
    """Verifies strict Section 138 / 142 statutory timelines.
    1. Demand Notice sent within 30 days of Memo.
    2. Cause of action arises after 15 days cure period.
    3. Complaint filed within 30 days of cause of action.
    """
    memo_date = parse_date(memo_date_str)
    notice_date = parse_date(notice_served_date_str)
    complaint_date = parse_date(complaint_date_str) if complaint_date_str else None

    results = {
        "statute": "Section 138 & 142 Negotiable Instruments Act, 1881",
        "valid": True,
        "warnings": [],
        "timeline_stages": []
    }

    if memo_date and notice_date:
        notice_delta = (notice_date - memo_date).days
        results["timeline_stages"].append({
            "stage": "Statutory Demand Notice Service",
            "elapsed_days": notice_delta,
            "statutory_limit_days": 30,
            "status": "PASS" if notice_delta <= 30 else "BARRED"
        })
        if notice_delta > 30:
            results["valid"] = False
            results["warnings"].append(
                f"Statutory notice was served {notice_delta} days after dishonour memo (Statutory maximum is 30 days). Complaint liable to be quashed."
            )

        # Cure period (15 days)
        cure_end = notice_date + timedelta(days=15)
        results["timeline_stages"].append({
            "stage": "15-Day Cure Window",
            "cure_end_date": cure_end.strftime("%d/%m/%Y"),
            "status": "INFO"
        })

        if complaint_date:
            complaint_delta = (complaint_date - cure_end).days
            if complaint_delta < 0:
                results["valid"] = False
                results["warnings"].append(
                    f"Premature complaint! Filed {abs(complaint_delta)} days before the mandatory 15-day cure period expired."
                )
            elif complaint_delta > 30:
                results["valid"] = False
                results["warnings"].append(
                    f"Barred by limitation under Section 142(1)(b)! Complaint filed {complaint_delta} days after cause of action (Limit is 30 days). Condonation of delay required."
                )
            else:
                results["timeline_stages"].append({
                    "stage": "Formal Complaint Filing",
                    "elapsed_from_cause_of_action": complaint_delta,
                    "statutory_limit_days": 30,
                    "status": "PASS"
                })

    return results
