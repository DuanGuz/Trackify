# core/utils_push.py
import requests

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_expo_push(token: str, title: str, body: str, data=None):
    """
    Envía una notificación push a través del servicio de Expo.
    token: expo push token (ExponentPushToken[...])
    """
    if not token:
        return False, "Sin token"

    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},   
    }

    try:
        resp = requests.post(EXPO_PUSH_URL, json=payload, timeout=5)
        resp.raise_for_status()
        j = resp.json()
        return True, j
    except Exception as e:
        return False, str(e)
