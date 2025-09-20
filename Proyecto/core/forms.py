from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *

class RegistroGerenteForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        rol_gerente, created = Rol.objects.get_or_create(nombre='Gerente')
        user.rol = rol_gerente
        if commit:
            user.save()
        return user