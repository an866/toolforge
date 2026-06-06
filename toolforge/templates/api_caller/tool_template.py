import requests

def api_call(url="{{ url }}", method="{{ method }}", headers=None, data=None):
    headers = headers or {}
    if method == "GET":
        resp = requests.get(url, headers=headers)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        resp = requests.put(url, headers=headers, json=data)
    else:
        resp = requests.delete(url, headers=headers)
    return {"status_code": resp.status_code, "body": resp.text, "headers": dict(resp.headers)}
