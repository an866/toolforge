import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_file(filepath="{{ filepath }}", format="{{ format }}"):
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    content = p.read_text(encoding="utf-8")

    if format == "json":
        return json.loads(content)
    elif format == "csv":
        reader = csv.DictReader(content.splitlines())
        return [row for row in reader]
    elif format == "xml":
        root = ET.fromstring(content)
        return _xml_to_dict(root)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _xml_to_dict(element):
    result = {}
    for child in element:
        result[child.tag] = child.text or _xml_to_dict(child)
    return result
