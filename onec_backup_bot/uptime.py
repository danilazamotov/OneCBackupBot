from __future__ import annotations

import requests

def push_status(push_url: str, status: str, msg: str):
    if not push_url:
        return
    try:
        requests.get(push_url, params={"status": status, "msg": msg}, timeout=5)
    except Exception:
        pass
