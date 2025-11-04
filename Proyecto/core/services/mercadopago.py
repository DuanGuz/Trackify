# core/services/mercadopago.py
from django.conf import settings
import requests

BASE = "https://api.mercadopago.com"

def _headers_json():
    return {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _short(text, n): text = (text or "").strip(); return text if len(text) <= n else (text[: n - 3] + "...")

def _is_test_mode(): return getattr(settings, "MERCADOPAGO_ENV", "test") == "test"

def _force_test_buyer_email(payer_email: str | None) -> str:
    if _is_test_mode():
        tb = (getattr(settings, "MERCADOPAGO_TEST_BUYER_EMAIL", "") or "").strip()
        if tb: return tb.lower()
    return (payer_email or "").lower()

def create_plan_and_get_initpoint(amount: int, currency: str, cycle: str, reason: str, back_url: str):
    frequency = 12 if (cycle or "").upper() == "ANUAL" else 1
    payload = {
        "reason": _short(reason, 90) or "Trackify",
        "back_url": back_url,
        "auto_recurring": {
            "currency_id": currency,
            "transaction_amount": int(amount),
            "frequency": frequency,
            "frequency_type": "months",
        },
    }
    print("MP preapproval_plan.create REQUEST =>", payload)
    r = requests.post(f"{BASE}/preapproval_plan", headers=_headers_json(), json=payload, timeout=30)
    data = {"status": r.status_code, "response": {}}
    try: data["response"] = r.json()
    except Exception: data["response"] = {"raw": r.text}
    from pprint import pformat
    print("MP preapproval_plan.create RESULT  =>", r.status_code, pformat(data["response"]))
    return data

def create_preapproval(payer_email: str, amount: int, currency: str, cycle: str, reason: str, back_url: str | None = None):
    frequency = 12 if (cycle or "").upper() == "ANUAL" else 1
    effective_back_url = back_url or getattr(settings, "MERCADOPAGO_SUCCESS_URL", "")
    body = {
        "payer_email": _force_test_buyer_email(payer_email),
        "reason": _short(reason, 90) or "Trackify",
        "back_url": effective_back_url,
        "auto_recurring": {
            "currency_id": currency,
            "transaction_amount": int(amount),
            "frequency": frequency,
            "frequency_type": "months",
        },
    }
    print("MP preapproval.create REQUEST =>", body)
    r = requests.post(f"{BASE}/preapproval", headers=_headers_json(), json=body, timeout=30)
    data = {"status": r.status_code, "response": {}}
    try: data["response"] = r.json()
    except Exception: data["response"] = {"raw": r.text}
    from pprint import pformat
    print("MP preapproval.create RESULT  =>", r.status_code, pformat(data["response"]))
    return data

def get_preapproval(preapproval_id: str):
    """Consulta un preapproval por id, con logs útiles."""
    url = f"{BASE}/preapproval/{preapproval_id}"
    print("MP preapproval.get REQUEST =>", url)
    r = requests.get(url, headers=_headers_json(), timeout=30)
    data = {"status": r.status_code, "response": {}}
    try:
        data["response"] = r.json()
    except Exception:
        data["response"] = {"raw": r.text}
    from pprint import pformat
    print("MP preapproval.get RESULT  =>", r.status_code, pformat(data["response"]))
    return data

def search_preapprovals_by_plan(plan_id: str, limit: int = 10):
    """Busca suscripciones por plan. Devuelve las más recientes primero."""
    params = {
        "preapproval_plan_id": plan_id,
        "sort": "date_created",
        "criteria": "desc",
        "limit": limit,
    }
    r = requests.get(f"{BASE}/preapproval/search", headers=_headers_json(), params=params, timeout=30)
    data = {"status": r.status_code, "response": {}}
    try:
        data["response"] = r.json()
    except Exception:
        data["response"] = {"raw": r.text}
    return data

def search_preapprovals_all(limit=50, offset=0):
    url = f"{BASE}/preapproval/search?limit={int(limit)}&offset={int(offset)}"
    r = requests.get(url, headers=_headers_json(), timeout=30)
    data = {"status": r.status_code, "response": {}}
    try:
        data["response"] = r.json()
    except Exception:
        data["response"] = {"raw": r.text}
    return data

def search_preapprovals_by_email(payer_email: str, limit: int = 10, status: str | None = None):
    """
    Busca suscripciones por email (normalizado en minúsculas). Si `status` se da (p.ej. "authorized"),
    filtra por ese estado en la API.
    """
    email = (payer_email or "").strip().lower()
    params = {
        "payer_email": email,
        "sort": "date_created",
        "criteria": "desc",
        "limit": limit,
    }
    if status:
        params["status"] = status
    r = requests.get(f"{BASE}/preapproval/search", headers=_headers_json(), params=params, timeout=30)
    data = {"status": r.status_code, "response": {}}
    try:
        data["response"] = r.json()
    except Exception:
        data["response"] = {"raw": r.text}
    return data
