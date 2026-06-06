import re


def process_text(text="{{ text }}", pattern="{{ pattern }}", operation="{{ operation }}", replacement=""):
    if operation == "search":
        match = re.search(pattern, text)
        if match:
            return {"found": True, "match": match.group(0), "groups": match.groups(), "span": match.span()}
        return {"found": False, "match": None, "groups": None, "span": None}
    elif operation == "replace":
        result = re.sub(pattern, replacement, text)
        count = len(re.findall(pattern, text))
        return {"replaced": result, "count": count}
    elif operation == "split":
        parts = re.split(pattern, text)
        return {"parts": parts, "count": len(parts)}
    elif operation == "extract":
        matches = re.findall(pattern, text)
        return {"matches": matches, "count": len(matches)}
    else:
        raise ValueError(f"Unsupported operation: {operation}")
