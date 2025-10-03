from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *

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
            # si usas validación E.164, normaliza aquí
            u.telefono = str(telefono).strip()

        u.save()
        return Response({"detail": "Perfil actualizado."}, status=200)

class MisTareasAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Tarea.objects.filter(asignado=request.user).order_by("-created_at")
        return Response(TareaSerializer(qs, many=True).data)

class TareaEstadoAPI(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        try:
            tarea = Tarea.objects.get(pk=pk, asignado=request.user)
        except Tarea.DoesNotExist:
            return Response({"detail":"No encontrada"}, status=status.HTTP_404_NOT_FOUND)

        ser = TareaSerializer(tarea, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        ser.save()

        comentario = request.data.get("comentario")
        if comentario:
            Comentario.objects.create(
                tarea=tarea,
                usuario=request.user,
                contenido=str(comentario)[:1000],
            )

        return Response({"ok": True})

class MisEvaluacionesAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Evaluacion.objects.filter(trabajador=request.user).order_by("-created_at")
        return Response(EvaluacionSerializer(qs, many=True).data)
