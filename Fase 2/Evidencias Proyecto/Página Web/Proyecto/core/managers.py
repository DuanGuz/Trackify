# managers.py
from django.contrib.auth.models import UserManager as DjangoUserManager

class UserManager(DjangoUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not extra_fields.get("empresa"):
            raise ValueError("Debes proporcionar empresa")
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if not extra_fields.get("empresa"):
            # por ejemplo, asigna la primera empresa o crea una “Default”
            from .models import Empresa
            extra_fields["empresa"] = Empresa.objects.first() or Empresa.objects.create(nombre="Default")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email, password, **extra_fields)
