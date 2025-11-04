# core/middleware.py
from django.shortcuts import redirect
from django.http import JsonResponse
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

ALLOWED_PREFIXES = (
    "/admin/",
    "/static/",
    "/media/",
    "/login/",
    "/logout/",
    "/registro-web/",
    "/password-reset/",
    "/api/auth/",   # por si tienes endpoints de auth
    "/webhooks/mercadopago/",
    "/billing/checkout/",
    "/billing/success/",
    "/billing/failure/",
    "/billing/pending/",
    "/billing/refresh/",
)