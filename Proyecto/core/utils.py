# core/utils.py
import re
import unicodedata

TRACKIFY_DOMAIN = "trackify.com"

def _strip_accents(s: str) -> str:
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = _strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s

def clean_rut(rut: str) -> str:
    """Deja solo dígitos + DV (0-9 o K)."""
    rut = (rut or "").upper().replace(".", "").replace("-", "").strip()
    return rut

def calc_dv(cuerpo: int) -> str:
    """Calcula DV chileno (módulo 11)."""
    suma = 0
    multiplo = 2
    while cuerpo > 0:
        suma += (cuerpo % 10) * multiplo
        cuerpo //= 10
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)

def is_valid_rut(rut: str) -> bool:
    """Valida rut limpio (sin puntos/guión)."""
    rut = clean_rut(rut)
    if not re.match(r"^\d{7,8}[0-9K]$", rut):
        return False
    cuerpo = int(rut[:-1])
    dv = rut[-1]
    return calc_dv(cuerpo) == dv

def format_rut(rut: str) -> str:
    """xx.xxx.xxx-x a partir de rut limpio."""
    rut = clean_rut(rut)
    if len(rut) < 2 or not re.match(r"^\d+[0-9K]$", rut):
        return rut
    cuerpo, dv = rut[:-1], rut[-1]
    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_formateado}-{dv}"


def generate_username(primer_nombre: str, primer_apellido: str) -> str:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    base = f"{_norm(primer_apellido)[:1]}{_norm(primer_nombre)}" or "usuario"
    username, n = base, 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{n}"; n += 1
    return username

def generate_email(primer_nombre: str, primer_apellido: str, domain: str = TRACKIFY_DOMAIN) -> str:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    left = f"{_norm(primer_nombre)}.{_norm(primer_apellido)}"
    email, n = f"{left}@{domain}", 1
    while User.objects.filter(email=email).exists():
        email = f"{left}{n}@{domain}"; n += 1
    return email

def generate_password(primer_nombre: str, primer_apellido: str, rut: str) -> str:
    n1 = (_norm(primer_nombre)[:1] or "x").upper()
    a1 = (_norm(primer_apellido)[:1] or "x")
    rut_clean = clean_rut(rut)
    return f"{n1}{a1}{rut_clean}"
