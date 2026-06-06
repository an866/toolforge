import json
import csv
from io import StringIO


def convert(data, input_format="{{ input_format }}", output_format="{{ output_format }}"):
    if input_format == "json" and output_format == "csv":
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, list):
            raise ValueError("JSON data must be a list of objects to convert to CSV")

        output = StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()

    elif input_format == "csv" and output_format == "json":
        if isinstance(data, str):
            reader = csv.DictReader(StringIO(data))
            data = [row for row in reader]
        return json.dumps(data, indent=2, ensure_ascii=False)

    else:
        raise ValueError(f"Unsupported conversion: {input_format} -> {output_format}")
