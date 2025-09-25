# core/validators.py
from django.core.exceptions import ValidationError
from .utils import clean_rut, is_valid_rut
import re

def rut_validator(value: str):
    value = clean_rut(value)
    if not is_valid_rut(value):
        raise ValidationError("RUT inválido.")

E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")  # +<country><national> 8–15 dígitos totales

def validate_e164(value: str):
    if not value:
        return
    v = value.strip()
    if not E164_REGEX.match(v):
        raise ValidationError("Teléfono inválido. Usa formato E.164, p.ej. +56912345678")