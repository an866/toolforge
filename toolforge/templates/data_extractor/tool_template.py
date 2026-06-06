import re

_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    "url": r"https?://[^\s<>\"{}|\\^`\[\]]+",
    "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
    "number": r"-?\d+\.?\d*",
}


def extract(text="{{ text }}", pattern="{{ pattern }}", extract_type="{{ extract_type }}"):
    if extract_type == "custom" and pattern:
        regex = pattern
    else:
        regex = _PATTERNS.get(extract_type)
        if not regex:
            raise ValueError(f"Unsupported extract_type: {extract_type}")

    matches = re.findall(regex, text)
    unique = list(dict.fromkeys(matches))
    return {
        "extracted": unique,
        "count": len(unique),
        "type": extract_type,
    }
