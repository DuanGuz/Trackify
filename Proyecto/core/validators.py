# core/validators.py
from django.core.exceptions import ValidationError
from .utils import clean_rut, is_valid_rut

def rut_validator(value: str):
    value = clean_rut(value)
    if not is_valid_rut(value):
        raise ValidationError("RUT inválido.")
