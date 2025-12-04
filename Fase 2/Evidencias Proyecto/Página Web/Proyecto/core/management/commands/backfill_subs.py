from django.core.management.base import BaseCommand
from core.models import Empresa, SuscripcionEmpresa

class Command(BaseCommand):
    help = "Crea SuscripcionEmpresa para empresas que no la tienen"

    def handle(self, *args, **kwargs):
        created = 0
        for e in Empresa.objects.all():
            _, was_created = SuscripcionEmpresa.objects.get_or_create(empresa=e)
            created += 1 if was_created else 0
        self.stdout.write(self.style.SUCCESS(f"Listo. Suscripciones creadas: {created}"))
