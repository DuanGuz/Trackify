# core/utils_sms.py
import random
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.utils import timezone

from .models import PasswordResetSMS

User = get_user_model()

def generar_otp(length=6):
    # 6 dígitos, con ceros a la izquierda
    return f"{random.randint(0, 10**length - 1):0{length}d}"

def crear_reset_sms(user, minutos_expira=10):
    # invalida códigos anteriores no usados
    PasswordResetSMS.objects.filter(user=user, used=False).update(used=True)

    code = generar_otp()
    hashed = make_password(code)
    obj = PasswordResetSMS.objects.create(
        user=user,
        telefono=user.telefono,
        code_hash=hashed,
        expires_at=timezone.now() + timedelta(minutes=minutos_expira),
    )
    return obj, code

def verificar_otp(reset_obj: PasswordResetSMS, code: str) -> bool:
    if not reset_obj.can_attempt():
        return False
    reset_obj.intentos += 1
    ok = check_password(code, reset_obj.code_hash)
    if ok:
        reset_obj.used = True
    reset_obj.save(update_fields=["intentos", "used"])
    return ok

# --- Rate limit por teléfono e IP (simple) ---
def _cache_key(prefix, value):
    return f"smsrl:{prefix}:{value}"

def check_rate_limit(telefono: str, ip: str, max_por_hora=5):
    # limita envíos de OTP
    tel_key = _cache_key("tel", telefono)
    ip_key  = _cache_key("ip", ip or "unknown")

    tel_count = cache.get(tel_key, 0)
    ip_count  = cache.get(ip_key, 0)

    if tel_count >= max_por_hora or ip_count >= max_por_hora:
        return False

    # incrementa por 1 hora
    cache.set(tel_key, tel_count + 1, 60*60)
    cache.set(ip_key, ip_count + 1, 60*60)
    return True


# --- Enviar SMS: backend simple con Twilio o consola ---
def send_sms(telefono: str, mensaje: str):
    backend = getattr(settings, "SMS_BACKEND", "console")
    if backend == "twilio":
        try:
            from twilio.rest import Client
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token  = settings.TWILIO_AUTH_TOKEN
            client = Client(account_sid, auth_token)

            messaging_sid = getattr(settings, "TWILIO_MESSAGING_SERVICE_SID", "")
            if messaging_sid:
                msg = client.messages.create(
                    to=telefono,
                    messaging_service_sid=messaging_sid,
                    body=mensaje
                )
            else:
                from_num = settings.TWILIO_FROM_NUMBER
                msg = client.messages.create(
                    to=telefono,
                    from_=from_num,
                    body=mensaje
                )
            # Opcional: log de estado
            print("[Twilio] sent sid:", msg.sid, "status:", msg.status)
            return True, None
        except Exception as e:
            # Log detallado
            import traceback
            traceback.print_exc()
            return False, str(e)
    elif backend == "console":
        print(f"[SMS Console] -> {telefono}: {mensaje}")
        return True, None
    return False, "SMS backend inválido"

