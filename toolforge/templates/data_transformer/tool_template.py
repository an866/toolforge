def transform_data(data, operation="{{ operation }}", key=None, value=None, reverse=False):
    if operation == "filter":
        if callable(value):
            return [item for item in data if value(item)]
        elif key is not None and value is not None:
            return [item for item in data if item.get(key) == value]
        return data
    elif operation == "map":
        if callable(value):
            return [value(item) for item in data]
        elif key is not None:
            return [item.get(key) for item in data if isinstance(item, dict)]
        return [str(item) for item in data]
    elif operation == "sort":
        if isinstance(data, list):
            if key:
                return sorted(data, key=lambda x: x.get(key) if isinstance(x, dict) else x, reverse=reverse)
            return sorted(data, reverse=reverse)
        return data
    elif operation == "group":
        result = {}
        if key is not None:
            for item in data:
                k = item.get(key) if isinstance(item, dict) else item
                result.setdefault(k, []).append(item)
        return result
    elif operation == "flatten":
        flat = []
        for item in data:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat
    else:
        raise ValueError(f"Unsupported operation: {operation}")
