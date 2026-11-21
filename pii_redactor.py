import re

def redact_pii(text: str) -> dict:
    """Detects and masks sensitive personal data (Aadhaar, PAN, Phone, Email, Bank A/C)
    before sending text to external LLM providers.
    """
    if not text:
        return {"redacted_text": "", "redactions_count": 0, "types_found": []}
        
    redactions = 0
    types_found = set()
    s = text

    # 1. Aadhaar Number (12 digits, optional space/hyphen)
    aadhaar_pattern = r"\b[2-9]{1}[0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b"
    if re.search(aadhaar_pattern, s):
        s = re.sub(aadhaar_pattern, "[REDACTED_AADHAAR]", s)
        types_found.add("Aadhaar")
        redactions += 1

    # 2. Indian PAN Card (5 letters, 4 digits, 1 letter)
    pan_pattern = r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"
    if re.search(pan_pattern, s):
        s = re.sub(pan_pattern, "[REDACTED_PAN]", s)
        types_found.add("PAN")
        redactions += 1

    # 3. Phone Numbers (10 digits, +91 optional)
    phone_pattern = r"(?:\+91[\-\s]?)?[6789]\d{9}\b"
    if re.search(phone_pattern, s):
        s = re.sub(phone_pattern, "[REDACTED_PHONE]", s)
        types_found.add("Phone")
        redactions += 1

    # 4. Email Addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    if re.search(email_pattern, s):
        s = re.sub(email_pattern, "[REDACTED_EMAIL]", s)
        types_found.add("Email")
        redactions += 1

    # 5. Bank Account Numbers (9-18 continuous digits)
    bank_pattern = r"\b\d{11,18}\b"
    if re.search(bank_pattern, s):
        s = re.sub(bank_pattern, "[REDACTED_ACCOUNT]", s)
        types_found.add("Bank_Account")
        redactions += 1

    return {
        "redacted_text": s,
        "redactions_count": redactions,
        "types_found": list(types_found)
    }
