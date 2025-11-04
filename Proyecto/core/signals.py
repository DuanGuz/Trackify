# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Empresa, SuscripcionEmpresa

@receiver(post_save, sender=Empresa)
def crear_suscripcion_por_defecto(sender, instance, created, **kwargs):
    if created:
        # Evita duplicados si ya existe
        SuscripcionEmpresa.objects.get_or_create(empresa=instance)
