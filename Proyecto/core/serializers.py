from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'rol']
        
class TareaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarea
        fields = ["id","titulo","descripcion","estado","fecha_limite","created_at","updated_at"]

class TareaSerializer(serializers.ModelSerializer):
    fecha_limite_fmt = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = ["id","titulo","descripcion","estado","fecha_limite","created_at","updated_at",
                  "fecha_limite_fmt","created_at_fmt"]

    def get_fecha_limite_fmt(self, obj):
        return obj.fecha_limite.strftime("%d/%m/%Y") if obj.fecha_limite else None

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None


class EvaluacionSerializer(serializers.ModelSerializer):
    supervisor_nombre = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Evaluacion
        fields = ["id","puntaje","comentarios","created_at","created_at_fmt","supervisor_nombre"]

    def get_supervisor_nombre(self, obj):
        s = obj.supervisor
        return f"{getattr(s,'primer_nombre','')} {getattr(s,'primer_apellido','')}".strip()

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None