from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation
from .models import Tarea, Evaluacion, Notificacion, Comentario

User = get_user_model()


# =========================
# 1) Usuario / Perfil
# =========================

class UserSerializer(serializers.ModelSerializer):
    """
    Versión simple (por si ya la usas en otras partes).
    """
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "rol", "rol_nombre"]


class UserPerfilSerializer(serializers.ModelSerializer):
    """
    Pensado para la app móvil: muestra lo que el trabajador ve de sí mismo.
    TODO es solo lectura (RRHH mantiene los datos reales).
    """
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)
    departamento_nombre = serializers.CharField(source="departamento.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "primer_nombre",
            "segundo_nombre",
            "primer_apellido",
            "segundo_apellido",
            "email",
            "rol_nombre",
            "departamento_nombre",
            "empresa_nombre",
        ]
        read_only_fields = fields  # <- todo read-only para la app


# =========================
# 2) Tareas
# =========================

class TareaSerializer(serializers.ModelSerializer):
    """
    Serializer de tareas para listar/mostrar en la app.
    Incluye fechas con formato amigable.
    """
    fecha_limite_fmt = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = [
            "id",
            "titulo",
            "descripcion",
            "estado",
            "fecha_limite",
            "created_at",
            "updated_at",
            "fecha_limite_fmt",
            "created_at_fmt",
        ]

    def get_fecha_limite_fmt(self, obj):
        return obj.fecha_limite.strftime("%d/%m/%Y") if obj.fecha_limite else None

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None


class TareaEstadoSerializer(serializers.Serializer):
    
    estado = serializers.ChoiceField(choices=[e[0] for e in Tarea.ESTADOS])
    comentario = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,   # 👈 clave para aceptar null
        max_length=1000,
    )

    class Meta:
        model = Tarea
        fields = ["estado", "comentario"]

    def validate_estado(self, value):
        # Opcional: limitar a los choices definidos en el modelo.
        estados_validos = [e[0] for e in Tarea.ESTADOS]
        if value not in estados_validos:
            raise serializers.ValidationError("Estado no válido.")
        return value


# =========================
# 3) Evaluaciones
# =========================

class EvaluacionSerializer(serializers.ModelSerializer):
    supervisor_nombre = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Evaluacion
        fields = ["id","puntaje","comentarios","created_at","created_at_fmt","supervisor_nombre"]

    def get_supervisor_nombre(self, obj):
        s = obj.evaluador   # 👈 AQUÍ EL CAMBIO
        return f"{getattr(s,'primer_nombre','')} {getattr(s,'primer_apellido','')}".strip()

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None

# =========================
# 4) Notificaciones
# =========================

class NotificacionSerializer(serializers.ModelSerializer):
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = [
            "id",
            "mensaje",
            "is_read",
            "created_at",
            "created_at_fmt",
        ]

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None


# =========================
# 5) Comentarios (opcional)
# =========================

class ComentarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = [
            "id",
            "contenido",
            "created_at",
            "created_at_fmt",
            "usuario_nombre",
        ]

    def get_usuario_nombre(self, obj):
        u = obj.usuario
        return f"{getattr(u, 'primer_nombre', '')} {getattr(u, 'primer_apellido', '')}".strip()

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None


# =========================
# 6) Cambio de contraseña (APP)
# =========================

class PasswordChangeSerializer(serializers.Serializer):
    """
    Para que el trabajador pueda cambiar su contraseña desde la app.
    - Verifica la contraseña actual.
    - Valida la nueva con los validadores de Django.
    """
    old_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user

        # 1) Comprobar contraseña actual
        if not user.check_password(attrs.get("old_password")):
            raise serializers.ValidationError({"old_password": "La contraseña actual es incorrecta."})

        # 2) Comprobar que coincidan
        if attrs.get("new_password1") != attrs.get("new_password2"):
            raise serializers.ValidationError({"new_password2": "Las contraseñas no coinciden."})

        # 3) Validar con las reglas de Django (longitud mínima, etc.)
        password_validation.validate_password(attrs.get("new_password1"), user=user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        new_password = self.validated_data["new_password1"]
        user.set_password(new_password)
        user.save()
        return user


class ComentarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = ["id", "contenido", "created_at", "created_at_fmt", "usuario_nombre"]

    def get_usuario_nombre(self, obj):
        u = obj.usuario
        return f"{getattr(u, 'primer_nombre', '')} {getattr(u, 'primer_apellido', '')}".strip()

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None


class TareaDetalleSerializer(serializers.ModelSerializer):
    fecha_limite_fmt = serializers.SerializerMethodField()
    created_at_fmt = serializers.SerializerMethodField()
    comentarios = ComentarioSerializer(
        many=True,
        read_only=True,
        source="comments",  
    )

    class Meta:
        model = Tarea
        fields = [
            "id",
            "titulo",
            "descripcion",
            "estado",
            "fecha_limite",
            "created_at",
            "updated_at",
            "fecha_limite_fmt",
            "created_at_fmt",
            "comentarios",  
        ]

    def get_fecha_limite_fmt(self, obj):
        return obj.fecha_limite.strftime("%d/%m/%Y") if obj.fecha_limite else None

    def get_created_at_fmt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M") if obj.created_at else None