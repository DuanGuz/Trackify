from django import template

register = template.Library()

ZERO_DEC = {"CLP", "JPY", "PYG"}

@register.filter
def money_cents(cents, currency: str):
    """
    Renderiza un monto expresado en "centavos" según la moneda.
    - Monedas sin decimales (CLP/JPY/PGY): muestra entero con miles (puntos).
    - Otras: divide por 100 y muestra 2 decimales.
    Uso en template:
        {{ sub.price_cents|money_cents:sub.currency }}
    """
    currency = (currency or "").upper()
    try:
        cents = int(cents or 0)
    except Exception:
        cents = 0

    if currency in ZERO_DEC:
        # 15000 -> "15.000"
        return f"{cents:,}".replace(",", ".")
    # 2900 -> "29.00"
    return f"{cents/100:.2f}"
