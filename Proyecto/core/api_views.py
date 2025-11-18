from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.utils.timezone import localtime
from .models import (
    Tarea, Evaluacion, Comentario, HistorialTarea
)
from .serializers import *
from django.contrib.auth import get_user_model
User = get_user_model()

from django.contrib.auth import password_validation
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

# ================================================================
# 1) PERFIL DEL TRABAJADOR
# ================================================================

class MeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        data = {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "telefono": getattr(u, "telefono", "") or "",
            "primer_nombre": getattr(u, "primer_nombre", "") or "",
            "segundo_nombre": getattr(u, "segundo_nombre", "") or "",
            "primer_apellido": getattr(u, "primer_apellido", "") or "",
            "segundo_apellido": getattr(u, "segundo_apellido", "") or "",
            "rut": getattr(u, "rut", "") or "",
        }
        return Response(data, status=200)

    def patch(self, request):
        u = request.user
        email = request.data.get("email")
        telefono = request.data.get("telefono")

        if email is not None:
            u.email = email.strip()
        if telefono is not None:
            u.telefono = str(telefono).strip()

        u.save()
        return Response({"detail": "Perfil actualizado."}, status=200)


# ================================================================
# 2) LISTAR MIS TAREAS
# ================================================================

class MisTareasAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Tarea.objects.filter(
                asignado=request.user,
                empresa=request.user.empresa
            )
            .order_by("-created_at")
        )
        return Response(TareaSerializer(qs, many=True).data, status=200)


# ================================================================
# 3) CAMBIAR ESTADO DE TAREA + COMENTARIO
# ================================================================

class TareaEstadoAPI(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        tarea = get_object_or_404(
            Tarea,
            pk=pk,
            asignado=request.user,
            empresa=request.user.empresa,
        )

        ser = TareaEstadoSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        nuevo_estado = ser.validated_data["estado"]
        comentario_txt = (ser.validated_data.get("comentario") or "").strip()

        estado_anterior = tarea.estado

        # Cambiar estado si corresponde
        if nuevo_estado != estado_anterior:
            tarea.estado = nuevo_estado
            tarea.save(update_fields=["estado", "updated_at"])

            HistorialTarea.objects.create(
                tarea=tarea,
                accion="ESTADO",
                campo="estado",
                valor_anterior=estado_anterior,
                valor_nuevo=nuevo_estado,
                realizado_por=request.user,
                empresa=request.user.empresa,
            )

        # Comentario opcional
        if comentario_txt:
            Comentario.objects.create(
                tarea=tarea,
                usuario=request.user,
                contenido=comentario_txt[:1000],
                empresa=request.user.empresa,
            )
            HistorialTarea.objects.create(
                tarea=tarea,
                accion="COMENTARIO",
                campo="comentario",
                valor_nuevo=comentario_txt[:1000],
                realizado_por=request.user,
                empresa=request.user.empresa,
            )

        return Response({"ok": True}, status=200)



# ================================================================
# 4) MIS EVALUACIONES
# ================================================================

class MisEvaluacionesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Evaluacion.objects.filter(
                evaluado=request.user,
                empresa=request.user.empresa
            )
            .order_by("-created_at")
        )
        return Response(EvaluacionSerializer(qs, many=True).data, status=200)


# ================================================================
# 5) LISTAR NOTIFICACIONES
# ================================================================

class NotificacionesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Notificacion.objects
            .filter(usuario=request.user, empresa=request.user.empresa)
            .order_by("-created_at")
        )
        data = []
        for n in qs:
            data.append({
                "id": n.id,
                "mensaje": n.mensaje,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
                "created_at_fmt": n.created_at.strftime("%d/%m/%Y %H:%M"),
            })
        return Response({"items": data}, status=200)


# ================================================================
# 6) MARCAR TODAS COMO LEÍDAS
# ================================================================

class NotificacionesMarcarLeidasAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(
            usuario=request.user,
            is_read=False,
            empresa=request.user.empresa
        ).update(is_read=True)
        return Response({"ok": True})


# ================================================================
# 7) BORRAR TODAS LAS NOTIFICACIONES
# ================================================================

class NotificacionesBorrarAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        Notificacion.objects.filter(
            usuario=request.user,
            empresa=request.user.empresa
        ).delete()
        return Response({"ok": True})
    

class ChangePasswordAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old = request.data.get("old_password")
        new1 = request.data.get("new_password1")
        new2 = request.data.get("new_password2")

        if not old or not new1 or not new2:
            return Response({"detail": "Faltan campos."}, status=400)

        user = request.user

        # validar contraseña actual
        if not user.check_password(old):
            return Response({"detail": "La contraseña actual es incorrecta."}, status=400)

        # validar coincidencia
        if new1 != new2:
            return Response({"detail": "Las contraseñas no coinciden."}, status=400)

        # validadores de Django (mayúsculas, longitud, etc)
        try:
            password_validation.validate_password(new1, user)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        user.set_password(new1)
        user.save()

        return Response({"ok": True, "detail": "Contraseña actualizada correctamente."})
    

class PasswordChangeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        p1 = request.data.get("new_password1") or ""
        p2 = request.data.get("new_password2") or ""

        if not p1 or not p2:
            return Response(
                {"detail": "Debes ingresar ambas contraseñas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if p1 != p2:
            return Response(
                {"detail": "Las contraseñas no coinciden."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar con las reglas de Django
        try:
            validate_password(p1, user=user)
        except DjangoValidationError as e:
            return Response(
                {
                    "detail": "La contraseña no cumple los requisitos.",
                    "errors": e.messages,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(p1)
        user.save()

        # Opcional: el cliente móvil puede decidir cerrar sesión luego
        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )
    
class NotificacionesListAPI(APIView):
    """
    Lista las notificaciones del usuario autenticado (para la app móvil).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Notificacion.objects
            .filter(usuario=request.user)
            .order_by("-created_at")[:100]
        )

        items = []
        unread = 0
        for n in qs:
            if not n.is_read:
                unread += 1
            created_local = localtime(n.created_at)
            items.append({
                "id": n.id,
                "mensaje": n.mensaje,
                "is_read": n.is_read,
                "created_at": created_local.isoformat(),
                "created_at_fmt": created_local.strftime("%d/%m/%Y %H:%M"),
            })

        return Response({"items": items, "unread_count": unread}, status=200)


class NotificacionesClearAPI(APIView):
    """
    Marca como leídas todas las notificaciones del usuario.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(
            usuario=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({"ok": True}, status=200)


class NotificacionesDeleteAllAPI(APIView):
    """
    Elimina todas las notificaciones del usuario.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(usuario=request.user).delete()
        return Response({"ok": True}, status=200)

class RegisterExpoTokenAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = (request.data.get("expo_push_token") or "").strip()
        if not token:
            return Response({"detail": "Token requerido."}, status=status.HTTP_400_BAD_REQUEST)

        u = request.user
        u.expo_push_token = token
        u.save(update_fields=["expo_push_token"])
        return Response({"detail": "Token registrado."}, status=status.HTTP_200_OK)
    
class TareaDetalleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tarea = get_object_or_404(
            Tarea,
            pk=pk,
            asignado=request.user,
            empresa=request.user.empresa,
        )
        ser = TareaDetalleSerializer(tarea)
        return Response(ser.data, status=200)