from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth import get_user_model
from .models import *
from datetime import date
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.utils.translation import gettext_lazy as _
from django.db import transaction, IntegrityError


User = get_user_model()
# ========== Registro inicial (crea empresa + RRHH) ==========
class RegistroRRHHForm(UserCreationForm):
    email = forms.EmailField(required=True)
    username = forms.CharField(
        label='Nombre de usuario',
        help_text='Requerido. 150 caracteres máx. Letras, dígitos y @/./+/-/_',
        max_length=150
    )
    telefono = forms.CharField(
        label="Teléfono",
        help_text="Formato E.164 (ej: +56912345678)",
        required=True,
        validators=[validate_e164],
    )
    # Campo extra SOLO del form (no está en User)
    empresa_nombre = forms.CharField(label="Nombre de la empresa", max_length=150)

    class Meta:
        model = User
        # OJO: no incluir empresa_nombre aquí
        fields = [
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'rut', 'telefono', 'username', 'email', 'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_rut(self):
        rut = clean_rut(self.cleaned_data.get('rut', ''))
        if not is_valid_rut(rut):
            raise ValidationError("RUT inválido.")
        return rut

    def clean_username(self):
        u = (self.cleaned_data.get('username') or '').strip()
        if not u:
            raise ValidationError("El nombre de usuario es obligatorio.")
        # Username es ÚNICO GLOBAL en AbstractUser
        if User.objects.filter(username=u).exists():
            raise ValidationError("Este nombre de usuario ya está en uso en el sistema.")
        return u

    @transaction.atomic
    def save(self, commit=True):
        """
        Crea (o reutiliza) Empresa + Suscripción + Roles base y luego el usuario RRHH.
        TODO con get_or_create para evitar duplicados.
        """
        nombre_empresa = (self.cleaned_data['empresa_nombre'] or '').strip()

        # 1) Empresa (reutiliza si ya existe con el mismo nombre)
        empresa, _ = Empresa.objects.get_or_create(nombre=nombre_empresa)

        # 2) Suscripción (NO usar create() a ciegas)
        SuscripcionEmpresa.objects.get_or_create(empresa=empresa)

        # 3) Roles base únicos por empresa
        roles = {}
        for nombre in ["Recursos humanos", "Gerente", "Supervisor", "Trabajador"]:
            rol, _ = Rol.objects.get_or_create(empresa=empresa, nombre=nombre)
            roles[nombre] = rol

        # 4) Usuario RRHH
        user = super().save(commit=False)  # ya trae username + password hash
        user.email = self.cleaned_data['email']
        user.empresa = empresa
        user.rol = roles["Recursos humanos"]
        user.departamento = None
        user.telefono = self.cleaned_data['telefono']

        if commit:
            user.full_clean()
            user.save()

        return user

# ========== Gestión de usuarios (RRHH) ==========
class RegistroUsuarioRRHHForm(forms.ModelForm):
    """
    Formulario que usa RRHH para crear usuarios de su empresa.
    Reglas:
      - Filtra Rol y Departamento por empresa.
      - Trabajador/Supervisor requieren Departamento.
      - RRHH NO debe tener Departamento (se fuerza a None).
      - RUT y Teléfono únicos por empresa.
    """
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.none(),
        required=True,
        label="Rol",
        help_text="Selecciona el rol del usuario"
    )
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(),
        required=False,
        label="Departamento"
    )
    telefono = forms.CharField(
        label="Teléfono",
        required=True,  # Recomendado obligatorio para flujo de SMS
        help_text="Formato E.164 (ej: +56912345678)",
        validators=[validate_e164],
    )

    class Meta:
        model = User
        fields = [
            'primer_nombre','segundo_nombre','primer_apellido','segundo_apellido',
            'rut','telefono','rol','departamento'
        ]

    def __init__(self, *args, **kwargs):
        # Inyectamos empresa desde la vista
        self.empresa: Empresa | None = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)

        # Filtrar SIEMPRE por empresa
        base_roles = Rol.objects.none()
        base_deptos = Departamento.objects.none()
        if self.empresa:
            base_roles = Rol.objects.filter(empresa=self.empresa).order_by('nombre')
            base_deptos = Departamento.objects.filter(empresa=self.empresa).order_by('nombre')

        self.fields['rol'].queryset = base_roles
        self.fields['departamento'].queryset = base_deptos

        # Por si viene sin empresa en instance (defensa)
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

    def clean(self):
        # Reafirma empresa en la instance antes del clean base
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

        cleaned = super().clean()
        rol = cleaned.get('rol')
        depto = cleaned.get('departamento')

        # Coherencia empresa–rol/depto
        if self.empresa:
            if rol and rol.empresa_id != self.empresa.id:
                self.add_error('rol', "El rol no pertenece a tu empresa.")
            if depto and depto.empresa_id != self.empresa.id:
                self.add_error('departamento', "El departamento no pertenece a tu empresa.")

        # Reglas por rol
        if rol and rol.nombre in ('Trabajador', 'Supervisor') and not depto:
            self.add_error('departamento', "Este campo es obligatorio para Trabajadores y Supervisores.")

        # Si es RRHH, forzamos sin departamento
        if rol and rol.nombre == 'Recursos humanos':
            cleaned['departamento'] = None
            self.instance.departamento = None

        return cleaned

    def clean_rut(self):
        rut = clean_rut(self.cleaned_data.get("rut", ""))
        if not is_valid_rut(rut):
            raise forms.ValidationError("RUT inválido.")
        qs = User.objects.filter(rut=rut)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT en tu empresa.")
        return rut

    def clean_telefono(self):
        tel = (self.cleaned_data.get("telefono") or "").strip()
        # validate_e164 ya corre por validators; aquí validamos unicidad por empresa
        qs = User.objects.filter(telefono=tel)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if qs.exists():
            raise ValidationError("Ya existe un usuario con este teléfono en tu empresa.")
        return tel

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.empresa and not user.empresa_id:
            user.empresa = self.empresa
        # Si se crea un RRHH, garantizar depa None
        if user.rol and user.rol.nombre == 'Recursos humanos':
            user.departamento = None
        if commit:
            user.save()
        return user



class UserUpdateForm(forms.ModelForm):
    """
    Formulario de edición de usuarios (RRHH).
    Reglas:
      - Filtra Rol y Departamento por empresa.
      - Trabajador/Supervisor requieren Departamento.
      - RRHH NO debe tener Departamento (se fuerza a None).
      - RUT y Teléfono únicos por empresa (excluyendo al propio usuario).
    """
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(),
        required=False,
        label="Departamento"
    )
    telefono = forms.CharField(
        label="Teléfono",
        required=False,  # Puedes poner True si quieres forzarlo al editar
        help_text="Formato E.164 (ej: +56912345678)",
        validators=[validate_e164],
    )

    class Meta:
        model = User
        fields = [
            'primer_nombre','segundo_nombre','primer_apellido','segundo_apellido',
            'rut','telefono','rol','departamento'
        ]

    def __init__(self, *args, **kwargs):
        self.empresa: Empresa | None = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)

        # Querysets filtrados por empresa
        self.fields['rol'].queryset = Rol.objects.none()
        self.fields['departamento'].queryset = Departamento.objects.none()
        if self.empresa:
            self.fields['rol'].queryset = Rol.objects.filter(empresa=self.empresa).order_by('nombre')
            self.fields['departamento'].queryset = Departamento.objects.filter(empresa=self.empresa).order_by('nombre')

        # Asegura empresa en la instance
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

        # Preselección explícita (normalmente ya lo hace por instance)
        if self.instance and self.instance.pk:
            self.fields['rol'].initial = self.instance.rol
            self.fields['departamento'].initial = self.instance.departamento
            self.fields['telefono'].initial = self.instance.telefono

    def clean(self):
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

        cleaned = super().clean()
        rol = cleaned.get('rol')
        depto = cleaned.get('departamento')

        # Coherencia empresa–rol/depto
        if self.empresa:
            if rol and rol.empresa_id != self.empresa.id:
                self.add_error('rol', "El rol no pertenece a tu empresa.")
            if depto and depto.empresa_id != self.empresa.id:
                self.add_error('departamento', "El departamento no pertenece a tu empresa.")

        # Regla: Supervisor/Trabajador deben tener departamento
        if rol and rol.nombre in ('Trabajador', 'Supervisor') and not depto:
            self.add_error('departamento', "Este campo es obligatorio para Trabajadores y Supervisores.")

        # Si es RRHH, forzamos sin departamento
        if rol and rol.nombre == 'Recursos humanos':
            cleaned['departamento'] = None
            self.instance.departamento = None

        return cleaned

    def clean_rut(self):
        rut = clean_rut(self.cleaned_data.get("rut", ""))
        if not is_valid_rut(rut):
            raise forms.ValidationError("RUT inválido.")
        qs = User.objects.filter(rut=rut)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT en tu empresa.")
        return rut

    def clean_telefono(self):
        tel = (self.cleaned_data.get("telefono") or "").strip()
        # Si decides que sea opcional al editar:
        if not tel:
            return tel

        qs = User.objects.filter(telefono=tel)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if qs.exists():
            raise ValidationError("Ya existe un usuario con este teléfono en tu empresa.")
        return tel

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.empresa and not user.empresa_id:
            user.empresa = self.empresa
        # Si el rol quedó en RRHH, asegurar departamento None
        if user.rol and user.rol.nombre == 'Recursos humanos':
            user.departamento = None
        if commit:
            user.save()
        return user



# ========== Departamentos ==========
class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nombre', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        # Para validar unicidad por empresa
        self.empresa = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")

        qs = Departamento.objects.all()
        # Unicidad POR EMPRESA
        empresa_id = None
        if self.empresa:
            empresa_id = self.empresa.id
        elif self.instance and self.instance.empresa_id:
            empresa_id = self.instance.empresa_id
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        qs = qs.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un departamento con ese nombre en tu empresa.")
        return nombre
    
# ========== Tareas ==========
class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo','descripcion','departamento','asignado','fecha_limite']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows':3}),
            'fecha_limite': forms.DateInput(attrs={'type':'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.empresa = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)

        # 🔐 Asegura empresa en la instancia lo antes posible
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

        # 🗓️ Tope visual: no permitir elegir fechas anteriores a hoy en el datepicker
        try:
            hoy = timezone.localdate().isoformat()
            self.fields['fecha_limite'].widget.attrs['min'] = hoy
        except Exception:
            pass

        u = getattr(self.request, "user", None)
        self.fields['departamento'].queryset = Departamento.objects.none()
        self.fields['asignado'].queryset = User.objects.none()

        if not self.empresa or not u or not getattr(u, "rol", None):
            return

        # QS limitados por empresa
        self.fields['departamento'].queryset = Departamento.objects.filter(
            empresa=self.empresa
        ).order_by('nombre')

        if u.rol.nombre == 'Gerente':
            if u.departamento_id:
                self.fields['departamento'].initial = u.departamento
                self.fields['departamento'].queryset = self.fields['departamento'].queryset.filter(pk=u.departamento_id)
                self.fields['asignado'].queryset = User.objects.filter(
                    empresa=self.empresa, rol__nombre='Supervisor', departamento=u.departamento
                ).order_by('primer_apellido','primer_nombre')
            else:
                self.fields['asignado'].queryset = User.objects.filter(
                    empresa=self.empresa, rol__nombre='Supervisor'
                ).order_by('primer_apellido','primer_nombre')

        elif u.rol.nombre == 'Supervisor':
            if u.departamento_id:
                self.fields['departamento'].initial = u.departamento
                self.fields['departamento'].queryset = self.fields['departamento'].queryset.filter(pk=u.departamento_id)
                self.fields['departamento'].disabled = True
                self.fields['asignado'].queryset = User.objects.filter(
                    empresa=self.empresa, rol__nombre='Trabajador', departamento=u.departamento
                ).order_by('primer_apellido','primer_nombre')
            else:
                self.fields['asignado'].queryset = User.objects.filter(
                    empresa=self.empresa, rol__nombre='Trabajador'
                ).order_by('primer_apellido','primer_nombre')
        else:
            self.fields['asignado'].queryset = User.objects.none()

    # 🛑 Candado del lado servidor: no permitir fechas pasadas
    def clean_fecha_limite(self):
        f = self.cleaned_data.get('fecha_limite')
        if f and f < timezone.localdate():
            raise forms.ValidationError("La fecha límite no puede ser anterior a hoy.")
        return f

    def clean(self):
        # ✅ Asegura empresa en la instancia ANTES del full_clean del modelo
        if self.empresa and not getattr(self.instance, "empresa_id", None):
            self.instance.empresa = self.empresa

        cleaned = super().clean()
        u = getattr(self.request, "user", None)
        depto = cleaned.get('departamento')
        asignado = cleaned.get('asignado')

        if not u or not getattr(u, "rol", None):
            raise forms.ValidationError("Permisos insuficientes.")

        # Defensa en profundidad: empresa coherente
        if depto and getattr(depto, "empresa_id", None) != getattr(self.empresa, "id", None):
            self.add_error('departamento', "El departamento no pertenece a tu empresa.")
        if asignado and getattr(asignado, "empresa_id", None) != getattr(self.empresa, "id", None):
            self.add_error('asignado', "El usuario asignado no pertenece a tu empresa.")

        # Reglas por rol
        if u.rol.nombre == 'Gerente':
            if not asignado or asignado.rol is None or asignado.rol.nombre != 'Supervisor':
                self.add_error('asignado', "Debes asignar a un Supervisor.")
            if u.departamento_id and depto and depto.id != u.departamento_id:
                self.add_error('departamento', "Debes usar tu propio departamento.")
            if asignado and asignado.departamento_id != getattr(depto, "id", None):
                self.add_error('asignado', "El supervisor debe pertenecer a ese departamento.")

        elif u.rol.nombre == 'Supervisor':
            if not asignado or asignado.rol is None or asignado.rol.nombre != 'Trabajador':
                self.add_error('asignado', "Debes asignar a un Trabajador.")
            if u.departamento_id and depto and depto.id != u.departamento_id:
                self.add_error('departamento', "Debes usar tu propio departamento.")
            if asignado and asignado.departamento_id != getattr(depto, "id", None):
                self.add_error('asignado', "El trabajador debe pertenecer a ese departamento.")
        else:
            raise forms.ValidationError("No tienes permisos para crear tareas.")

        return cleaned


class TareaEstadoForm(forms.ModelForm):
    comentario = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':2}), help_text="Opcional")

    class Meta:
        model = Tarea
        fields = ['estado']

    def save(self, user=None, commit=True):
        tarea = super().save(commit=False)
        if commit:
            tarea.save()
            texto = (self.cleaned_data.get("comentario") or "").strip()
            if texto and user is not None:
                Comentario.objects.create(
                    tarea=tarea,
                    usuario=user,
                    contenido=texto,
                    empresa=user.empresa   # 👈 requerido por tu modelo
                )
        return tarea

# ========== Evaluaciones ==========
class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = Evaluacion
        fields = ["evaluado", "puntaje", "comentarios"]
        widgets = {"puntaje": forms.NumberInput(attrs={"min": 1, "max": 5, "step": 1})}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.empresa = kwargs.pop("empresa", None)
        super().__init__(*args, **kwargs)
        self.fields["puntaje"].label = "Puntaje (1–5)"

        user = getattr(self.request, "user", None)
        rol = getattr(getattr(user, "rol", None), "nombre", "")
        depto_id = getattr(getattr(user, "departamento", None), "id", None)

        base_qs = User.objects.filter(empresa=self.empresa) if self.empresa else User.objects.none()
        if rol == "Gerente":
            qs = base_qs.filter(rol__nombre="Supervisor", departamento_id=depto_id)
        elif rol == "Supervisor":
            qs = base_qs.filter(rol__nombre="Trabajador", departamento_id=depto_id)
        else:
            qs = base_qs.none()

        self.fields["evaluado"].queryset = qs.order_by("primer_apellido", "primer_nombre")

    def clean(self):
        cleaned = super().clean()
        user = getattr(self.request, "user", None)
        rol = getattr(getattr(user, "rol", None), "nombre", "")
        self.instance.evaluador = user
        self.instance.tipo = "SUPERVISOR" if rol == "Gerente" else "TRABAJADOR" if rol == "Supervisor" else None

        if self.instance and hasattr(self.instance, "empresa_id") and not self.instance.empresa_id and self.empresa:
            self.instance.empresa = self.empresa
        return cleaned
    
# ========== Perfil / Auth ==========
class PerfilForm(forms.ModelForm):
    telefono = forms.CharField(required=False, help_text="Ej: +56912345678", validators=[validate_e164])

    class Meta:
        model = User
        fields = ["primer_nombre","segundo_nombre","primer_apellido","segundo_apellido","rut","username","email","telefono"]

    def clean_rut(self):
        rut = (self.cleaned_data.get("rut") or "").strip()
        rut = rut.replace(".", "").replace("-", "").upper()
        if not rut.isalnum():
            raise forms.ValidationError("RUT no válido.")
        return rut   
    
class SMSRequestForm(forms.Form):
    identificador = forms.CharField(
        label="RUT, usuario o teléfono",
        help_text="Ingresa tu RUT (con o sin puntos/guión), tu usuario o tu teléfono."
    )
    def clean_identificador(self):
        v = (self.cleaned_data["identificador"] or "").strip()
        if not v:
            raise ValidationError("Campo requerido.")
        return v


class SMSCodeForm(forms.Form):
    code = forms.CharField(label="Código recibido por SMS", max_length=6)


class SMSChangePasswordForm(forms.Form):
    new_password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Repite la nueva contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password1"), cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "Las contraseñas no coinciden.")
        return cleaned
    
class PerfilSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        help_text=password_validators_help_text_html(),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "class": "form-control"}),
    )
    new_password2 = forms.CharField(
        label=_("Confirmar nueva contraseña"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "class": "form-control"}),
    )
    