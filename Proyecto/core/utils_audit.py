def registrar_cambios_tarea(tarea, original, user, campos):
    """
    Crea entradas en HistorialTarea por cada campo cambiado entre 'original' y 'tarea'.
    'campos' es una lista de nombres de atributo del modelo Tarea.
    """
    from .models import HistorialTarea
    for c in campos:
        antiguo = getattr(original, c, None)
        nuevo = getattr(tarea, c, None)
        # Normaliza FKs a texto legible
        if hasattr(antiguo, "__str__"):
            antiguo = str(antiguo) if antiguo is not None else None
        if hasattr(nuevo, "__str__"):
            nuevo = str(nuevo) if nuevo is not None else None
        if antiguo != nuevo:
            accion = "ACTUALIZADA"
            if c == "asignado":
                accion = "ASIGNACION"
            elif c == "fecha_limite":
                accion = "FECHA_LIM"
            HistorialTarea.objects.create(
                tarea=tarea,
                accion=accion,
                campo=c,
                valor_anterior=antiguo,
                valor_nuevo=nuevo,
                realizado_por=user
            )

def registrar_cambios_eval(evaluacion, original, user, campos):
    from .models import HistorialEvaluacion
    for c in campos:
        old = getattr(original, c, None)
        new = getattr(evaluacion, c, None)
        old_str = str(old) if old is not None else None
        new_str = str(new) if new is not None else None
        if old_str != new_str:
            HistorialEvaluacion.objects.create(
                evaluacion=evaluacion,
                accion="ACTUALIZADA",
                campo=c,
                valor_anterior=old_str,
                valor_nuevo=new_str,
                realizado_por=user
            )