from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from .validators import *
from .utils import *
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class CustomUserManager(DjangoUserManager):
    """
    Convierte el extra_field 'empresa' (pk o nombre) en una instancia Empresa
    antes de crear usuarios/superusuarios.
    """
    def _resolve_empresa(self, empresa):
        from .models import Empresa  # import local para evitar import circular
        if empresa is None:
            return None
        if isinstance(empresa, Empresa):
            return empresa

        # Permite ingresar PK (número) o nombre (string)
        try:
            pk = int(str(empresa).strip())
            return Empresa.objects.get(pk=pk)
        except (ValueError, Empresa.DoesNotExist):
            # Si no es pk válido, intenta por nombre (crea si no existe)
            obj, _ = Empresa.objects.get_or_create(nombre=str(empresa).strip())
            return obj

    def _create_user(self, username, email, password, **extra_fields):
        # Normaliza empresa (si viene desde createsuperuser)
        if 'empresa' in extra_fields:
            extra_fields['empresa'] = self._resolve_empresa(extra_fields.get('empresa'))
        return super()._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Flags obligatorios para superusuario
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        # Asegura empresa presente
        if 'empresa' not in extra_fields or extra_fields['empresa'] is None:
            raise ValueError("Debes proporcionar 'empresa' para el superusuario (id o nombre).")

        # Normaliza empresa
        extra_fields['empresa'] = self._resolve_empresa(extra_fields.get('empresa'))
        return super().create_superuser(username, email, password, **extra_fields)
    
# Modelo de Empresa
class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
    
# Modelo de Rol
class Rol(models.Model):
    nombre = models.CharField(max_length=50)  
    descripcion = models.TextField(blank=True, null=True) 
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="roles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="uniq_rol_nombre_por_empresa")
        ]

    def __str__(self):
        return self.nombre

# Modelo de Usuario
class User(AbstractUser):
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, blank=True, null=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, blank=True, null=True)
    rut = models.CharField(max_length=12, validators=[rut_validator])
    rol = models.ForeignKey("Rol", on_delete=models.SET_NULL, null=True, related_name='users')
    departamento = models.ForeignKey("Departamento", on_delete=models.SET_NULL, null=True, blank=True, related_name="miembros")
    telefono = models.CharField(
        max_length=16, blank=True, null=True,
        validators=[validate_e164],
        help_text="Formato E.164 (ej: +56912345678)"
    )
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="usuarios", null=False, blank=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = CustomUserManager()
    REQUIRED_FIELDS = ["email", "empresa"]



    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "rut"], name="uniq_rut_por_empresa"),
        ]

    def clean(self):
        super().clean()
        # Si tiene departamento, debe ser de la misma empresa
        if self.departamento and self.departamento.empresa_id != self.empresa_id:
            raise ValidationError("El departamento seleccionado no pertenece a la empresa del usuario.")
        
    def save(self, *args, **kwargs):
        self.rut = clean_rut(self.rut)
        super().save(*args, **kwargs)

    def rut_formateado(self):
        return format_rut(self.rut)

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido} ({self.username})"

# Modelo de Departamento
class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="departamentos", db_index=True)
    def __str__(self):
        return self.nombre
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="uniq_depto_nombre_por_empresa"),
        ]

# Modelo de Tarea
class Tarea(models.Model):
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('En progreso', 'En progreso'),
        ('Atrasada', 'Atrasada'),
        ('Finalizada', 'Finalizada'),
    ]
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    asignado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tareas_asignadas')
    creada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas_creadas')  # 👈 NUEVO
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="tareas", db_index=True)

    def clean(self):
        super().clean()
        errors = {}

        if self.departamento and self.departamento.empresa_id != self.empresa_id:
            errors["departamento"] = "El departamento no pertenece a la empresa de la tarea."

        if self.asignado and self.asignado.empresa_id != self.empresa_id:
            errors["asignado"] = "El asignado no pertenece a la empresa de la tarea."

        if self.creada_por and self.creada_por.empresa_id != self.empresa_id:
            errors["creada_por"] = "El creador no pertenece a la empresa de la tarea."

        # 💡 Regla de flujo: asignado debe pertenecer al mismo departamento de la tarea
        if self.asignado and self.departamento and self.asignado.departamento_id != self.departamento_id:
            errors["asignado"] = "El asignado debe pertenecer al mismo departamento de la tarea."

        if self.fecha_limite and self.fecha_limite < timezone.localdate():
            errors["fecha_limite"] = "La fecha límite no puede ser anterior a hoy."

        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
        
    def __str__(self):
        return self.titulo

# Modelo de Evaluación (Calificación de desempeño)
class Evaluacion(models.Model):
    TIPO = [
        ("SUPERVISOR", "Supervisor"),
        ("TRABAJADOR", "Trabajador"),
    ]
    evaluado = models.ForeignKey(User, on_delete=models.CASCADE, related_name="evaluaciones_recibidas")
    evaluador = models.ForeignKey(User, on_delete=models.CASCADE, related_name="evaluaciones_realizadas")
    tipo = models.CharField(max_length=20, choices=TIPO)
    puntaje = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentarios = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="evaluaciones", db_index=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if not self.evaluador or not self.evaluado:
            return

        # 1) Misma empresa en todos
        if self.evaluador.empresa_id != self.empresa_id or self.evaluado.empresa_id != self.empresa_id:
            raise ValidationError("Evaluador, evaluado y evaluación deben pertenecer a la misma empresa.")

        # 2) Reglas de flujo
        rol_eval = getattr(self.evaluador.rol, "nombre", "")
        rol_evad = getattr(self.evaluado.rol, "nombre", "")
        if self.tipo == "SUPERVISOR":
            if rol_eval != "Gerente" or rol_evad != "Supervisor":
                raise ValidationError("Para tipo SUPERVISOR: Gerente evalúa a Supervisor.")
        elif self.tipo == "TRABAJADOR":
            if rol_eval != "Supervisor" or rol_evad != "Trabajador":
                raise ValidationError("Para tipo TRABAJADOR: Supervisor evalúa a Trabajador.")

        # 3) Mismo departamento
        dept_eval = getattr(self.evaluador, "departamento", None)
        dept_evad = getattr(self.evaluado, "departamento", None)
        if getattr(dept_eval, "id", None) != getattr(dept_evad, "id", None):
            raise ValidationError("Evaluador y evaluado deben pertenecer al mismo departamento.")

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.evaluado} por {self.evaluador} ({self.puntaje})"

# Modelo de Notificación
class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    mensaje = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="notificaciones")

    def clean(self):
        super().clean()
        if self.usuario and self.usuario.empresa_id != self.empresa_id:
            raise ValidationError("La notificación y el usuario deben pertenecer a la misma empresa.")
    
    
    def __str__(self):
        return f"Notificación para {self.usuario.username}"

# Modelo de Comentario
class Comentario(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='comments')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    contenido = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="comentarios")

    def clean(self):
        super().clean()
        if self.tarea and self.tarea.empresa_id != self.empresa_id:
            raise ValidationError("El comentario y la tarea deben pertenecer a la misma empresa.")
        if self.usuario and self.usuario.empresa_id != self.empresa_id:
            raise ValidationError("El comentario y el usuario deben pertenecer a la misma empresa.")
        
    def __str__(self):
        return f"Comentario de {self.usuario.username} en {self.tarea.titulo}"

class HistorialTarea(models.Model):
    ACCIONES = [
        ("CREADA", "Creada"),
        ("ACTUALIZADA", "Actualizada"),
        ("ESTADO", "Cambio de estado"),
        ("ASIGNACION", "Cambio de asignación"),
        ("FECHA_LIM", "Cambio de fecha límite"),
        ("COMENTARIO", "Nuevo comentario"),
        ("ELIMINADA", "Eliminada"),
    ]
    tarea = models.ForeignKey('Tarea', on_delete=models.CASCADE, related_name='historial')
    accion = models.CharField(max_length=20, choices=ACCIONES)
    campo = models.CharField(max_length=50, blank=True, null=True)   
    valor_anterior = models.TextField(blank=True, null=True)
    valor_nuevo = models.TextField(blank=True, null=True)
    realizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="historial_tareas")

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.tarea and self.tarea.empresa_id and not self.empresa_id:
            self.empresa_id = self.tarea.empresa_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_accion_display()}] Tarea {self.tarea_id} ({self.created_at:%Y-%m-%d %H:%M})"


# (Opcional) Historial de Evaluaciones — preparado para extender luego
class HistorialEvaluacion(models.Model):
    ACCIONES = [
        ("CREADA", "Creada"),
        ("ACTUALIZADA", "Actualizada"),
        ("ELIMINADA", "Eliminada"),
    ]
    evaluacion = models.ForeignKey('Evaluacion', on_delete=models.CASCADE, related_name='historial')
    accion = models.CharField(max_length=20, choices=ACCIONES)
    campo = models.CharField(max_length=50, blank=True, null=True)
    valor_anterior = models.TextField(blank=True, null=True)
    valor_nuevo = models.TextField(blank=True, null=True)
    realizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE, related_name="historial_evaluaciones")

    def save(self, *args, **kwargs):
        if self.evaluacion and self.evaluacion.empresa_id and not self.empresa_id:
            self.empresa_id = self.evaluacion.empresa_id
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_accion_display()}] Eval {self.evaluacion_id} ({self.created_at:%Y-%m-%d %H:%M})"
    
class PasswordResetSMS(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resets_sms")
    telefono = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=128)  # hash del código, no guardes el OTP plano
    intentos = models.PositiveIntegerField(default=0)
    max_intentos = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def can_attempt(self):
        return (not self.used) and (not self.is_expired()) and (self.intentos < self.max_intentos)
    


################################################################################################
# --- enums / choices ---
class PlanEmpresa(models.TextChoices):
    UNICO = "UNICO", "Plan Único"

class CicloFact(models.TextChoices):
    MENSUAL = "MENSUAL", "Mensual"
    ANUAL   = "ANUAL", "Anual"

class EstadoSub(models.TextChoices):
    INACTIVA = "INACTIVA", "Inactiva"
    ACTIVA   = "ACTIVA", "Activa"
    PAUSADA  = "PAUSADA", "Pausada"
    CANCELADA= "CANCELADA", "Cancelada"
    ERROR    = "ERROR", "Error"

# --- modelo principal de suscripción ---
class SuscripcionEmpresa(models.Model):
    empresa = models.OneToOneField("Empresa", on_delete=models.CASCADE, related_name="suscripcion")
    plan = models.CharField(max_length=20, choices=PlanEmpresa.choices, default=PlanEmpresa.UNICO)
    ciclo = models.CharField(max_length=20, choices=CicloFact.choices, default=CicloFact.MENSUAL)

    # Moneda y precios
    currency = models.CharField(max_length=5, default="CLP")
    price_cents = models.PositiveIntegerField(default=1000)
    annual_price_cents = models.PositiveIntegerField(default=10000)

    # MercadoPago
    mp_preapproval_id = models.CharField(max_length=80, blank=True, null=True, db_index=True)
    mp_payer_email = models.EmailField(blank=True, null=True)
    mp_plan_id = models.CharField(max_length=80, blank=True, null=True, db_index=True)  # <-- NUEVO

    # Estado
    estado = models.CharField(max_length=20, choices=EstadoSub.choices, default=EstadoSub.INACTIVA)
    started_at = models.DateTimeField(blank=True, null=True)
    next_billing_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscripción de Empresa"
        verbose_name_plural = "Suscripciones de Empresas"

    # ======= Helpers de dinero/moneda =======
    def uses_zero_decimals(self) -> bool:
        """Monedas sin decimales en MP (CLP/JPY/PYG)."""
        return (self.currency or "").upper() in {"CLP", "JPY", "PYG"}

    def precio_actual_cents(self) -> int:
        """Devuelve el precio en centavos según el ciclo guardado."""
        return self.annual_price_cents if self.ciclo == CicloFact.ANUAL else self.price_cents

    def amount_for_cycle(self, ciclo: str | None = None):
        """
        Monto que DEBES enviar a MercadoPago en transaction_amount.
        - Si la moneda NO usa decimales: enviar entero (centavos = unidad).
        - Si usa decimales: enviar float con 2 decimales (centavos/100).
        """
        ciclo = ciclo or self.ciclo or CicloFact.MENSUAL
        cents = self.annual_price_cents if ciclo == CicloFact.ANUAL else self.price_cents
        if self.uses_zero_decimals():
            # CLP: MP espera entero (1000 => $1.000)
            return int(cents)
        # USD/EUR: MP espera float (29.00 => 2900 cents)
        return round(cents / 100.0, 2)

    def display_money(self, cents: int) -> str:
        """
        Render “humano”: para CLP -> miles con punto; para otras -> 2 decimales.
        Útil si quieres mostrar precios sin el filtro de template.
        """
        if self.uses_zero_decimals():
            return f"{int(cents):,}".replace(",", ".")
        return f"{cents/100:.2f}"

    def is_active(self):
        return self.estado == EstadoSub.ACTIVA

    def __str__(self):
        return f"Suscripción {self.empresa.nombre} [{self.estado}]"


# Log de eventos de Mercado Pago (webhooks)
class MercadoPagoEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=64)
    data = models.JSONField(default=dict)
    related_preapproval = models.CharField(max_length=80, blank=True, null=True, db_index=True)

    def __str__(self):
        return f"MP Event {self.tipo} {self.related_preapproval or ''}".strip()