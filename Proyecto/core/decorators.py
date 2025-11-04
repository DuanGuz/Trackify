# core/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def require_gs_and_sub(view_func):
    """
    Restringe acceso a usuarios:
      - autenticados
      - con suscripción activa (salvo superuser)
      - cuyo rol sea Gerente o Supervisor (salvo superuser)
    Redirige con mensajes si no cumple.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user

        # 1) Debe estar autenticado (por si no apilas @login_required)
        if not u.is_authenticated:
            messages.error(request, "Debes iniciar sesión.")
            return redirect("web_login")

        # 2) Suscripción activa (superuser pasa igual)
        if not u.is_superuser:
            empresa = getattr(u, "empresa", None)
            sus = getattr(empresa, "suscripcion", None)
            if not sus or not sus.is_active():
                messages.info(request, "Tu empresa necesita una suscripción activa para usar reportes.")
                return redirect("billing_overview")  # Ajusta si tu URL es otra

        # 3) Rol permitido (superuser pasa igual)
        rol = getattr(getattr(u, "rol", None), "nombre", "")
        if not u.is_superuser and rol not in ("Gerente", "Supervisor"):
            messages.error(request, "No tienes permisos para exportar reportes.")
            return redirect("home")

        # OK
        return view_func(request, *args, **kwargs)
    return _wrapped

def require_billing_role(view_func):
    """
    Permite gestionar pagos solo a: superuser, RRHH, Gerente.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            messages.info(request, "Inicia sesión para continuar.")
            return redirect("web_login")
        rol = getattr(getattr(u, "rol", None), "nombre", "")
        if not (u.is_superuser or rol in ("Recursos humanos", "Gerente")):
            messages.error(request, "No tienes permisos para gestionar la suscripción.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped