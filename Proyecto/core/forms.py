from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import *
from datetime import date
from django.core.exceptions import ValidationError

User = get_user_model()
#REGISTRO GERENTE:
class RegistroGerenteForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido', 'rut', 
                  'username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        rol_gerente, created = Rol.objects.get_or_create(nombre='Gerente')
        user.rol = rol_gerente
        if commit:
            user.save()
        return user

#GESTIÓN DE USUARIOS (RRHH):
class RegistroUsuarioRRHHForm(forms.ModelForm):
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.none(),  # se setea en __init__
        required=True,
        label="Rol",
        help_text="Selecciona el rol del usuario"
    )

    class Meta:
        model = User
        fields = [
            'primer_nombre','segundo_nombre','primer_apellido','segundo_apellido',
            'rut','rol'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Puedes limitar a roles permitidos para RRHH:
        # self.fields['rol'].queryset = Rol.objects.filter(nombre__in=['Trabajador','Supervisor','Gerente'])
        # O permitir todos:
        self.fields['rol'].queryset = Rol.objects.all().order_by('nombre')

    def clean_rut(self):
        rut = clean_rut(self.cleaned_data.get("rut", ""))
        if not is_valid_rut(rut):
            raise forms.ValidationError("RUT inválido.")
        if User.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT.")
        return rut

class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ['primer_nombre','segundo_nombre','primer_apellido','segundo_apellido','rut','username','email','rol']

    def clean_rut(self):
        rut = clean_rut(self.cleaned_data.get("rut", ""))
        if not is_valid_rut(rut):
            raise forms.ValidationError("RUT inválido.")
        # evitar duplicado al editar
        qs = User.objects.filter(rut=rut).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este RUT.")
        return rut

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nombre', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3})
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        # Unicidad case-insensitive
        qs = Departamento.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un departamento con ese nombre.")
        return nombre
    
class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo','descripcion','departamento','asignado','fecha_limite','estado']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows':3}),
            'fecha_limite': forms.DateInput(attrs={'type':'date'})
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Solo mostrar trabajadores en "asignado"
        self.fields['asignado'].queryset = User.objects.filter(rol__nombre='Trabajador').order_by('primer_apellido','primer_nombre')
        # Estado por defecto en crear
        if request and getattr(request.user, "rol", None) and request.user.rol.nombre in ['Gerente','Supervisor']:
            # Opción 1: quitar el campo del formulario
            self.fields.pop('estado', None)
            # (Opción 2 alternativa: self.fields['estado'].disabled = True)

    def clean_fecha_limite(self):
        f = self.cleaned_data['fecha_limite']
        if f < date.today():
            raise forms.ValidationError("La fecha límite no puede ser en el pasado.")
        return f


class TareaEstadoForm(forms.ModelForm):
    comentario = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':2}), help_text="Opcional")

    class Meta:
        model = Tarea
        fields = ['estado']  # solo estado cambia el trabajador

    def save(self, user=None, commit=True):
        tarea = super().save(commit=False)
        if commit:
            tarea.save()
            texto = self.cleaned_data.get("comentario", "").strip()
            # si llega comentario, lo guardamos
            comentario = self.cleaned_data.get("comentario")
            if texto and user is not None:
                Comentario.objects.create(tarea=tarea, usuario=user, contenido=texto)
        return tarea
    


class EvaluacionForm(forms.ModelForm):
    puntaje = forms.IntegerField(min_value=1, max_value=5, label="Puntaje (1-5)")

    class Meta:
        model = Evaluacion
        fields = ['trabajador', 'puntaje', 'comentarios']
        widgets = {'comentarios': forms.Textarea(attrs={'rows':3})}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)   # podría venir None
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # queryset SIEMPRE válido (nunca None)
        self.fields['trabajador'].queryset = User.objects.filter(
            rol__nombre='Trabajador'
        ).order_by('primer_apellido','primer_nombre')

    def clean(self):
        cleaned = super().clean()
        trabajador = cleaned.get('trabajador')
        req_user = getattr(self.request, "user", None)

        if req_user and trabajador and trabajador.pk == req_user.pk:
            raise forms.ValidationError("No puedes evaluarte a ti mismo.")
        if trabajador and (not trabajador.rol or trabajador.rol.nombre != 'Trabajador'):
            raise forms.ValidationError("Solo puedes evaluar a usuarios con rol Trabajador.")
        if req_user and (not getattr(req_user, "rol", None) or req_user.rol.nombre != 'Supervisor') and not getattr(req_user, "is_superuser", False):
            raise forms.ValidationError("Solo Supervisores pueden crear evaluaciones.")
        return cleaned
    
class PerfilForm(forms.ModelForm):

    telefono = forms.CharField(
        required=False,
        help_text="Ej: +56912345678",
        validators=[validate_e164]
    )
    
    class Meta:
        model = User
        fields = [
            "primer_nombre", "segundo_nombre",
            "primer_apellido", "segundo_apellido",
            "rut", "username", "email", "telefono",
        ]

    def clean_rut(self):
        rut = (self.cleaned_data.get("rut") or "").strip()
        # Normaliza/valida RUT si tienes util. Ejemplo básico:
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


class SMSVerifyForm(forms.Form):
    code = forms.CharField(label="Código recibido por SMS", max_length=6)
    new_password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Repite la nueva contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "Las contraseñas no coinciden.")
        return cleaned