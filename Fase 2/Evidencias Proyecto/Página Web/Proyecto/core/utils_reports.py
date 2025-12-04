from django.db.models import Q

def scope_tareas_por_rol(qs, user):
    """RRHH/Superuser: todo. Gerente/Supervisor: solo su departamento."""
    if not user.is_authenticated:
        return qs.none()
    if user.is_superuser or (getattr(user.rol, "nombre", "") == "Recursos humanos"):
        return qs
    depto = getattr(user, "departamento", None)
    if depto:
        qs = qs.filter(departamento=depto)
    else:
        qs = qs.none()
    return qs

def scope_evaluaciones_por_rol(qs, user):
    """
    RRHH/Superuser: todo.
    Gerente: evaluaciones de su departamento (tanto a SUPERVISORES como TRABAJADORES).
    Supervisor: SOLO evaluaciones de TRABAJADORES de su departamento (no ve evaluaciones de supervisores).
    """
    if not user.is_authenticated:
        return qs.none()
    rol = getattr(user.rol, "nombre", "")
    if user.is_superuser or rol == "Recursos humanos":
        return qs
    depto = getattr(user, "departamento", None)
    if not depto:
        return qs.none()
    if rol == "Gerente":
        return qs.filter(evaluado__departamento=depto)
    if rol == "Supervisor":
        return qs.filter(tipo="TRABAJADOR", evaluado__departamento=depto)
    # Otros roles no deberían acceder a reportes globales
    return qs.none()
