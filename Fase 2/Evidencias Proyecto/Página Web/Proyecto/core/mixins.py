from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.db.models import Q
from django.views.generic.list import MultipleObjectMixin


class SoloRRHHMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        try:
            return u.is_authenticated and u.rol and u.rol.nombre == 'Recursos humanos'
        except Exception:
            return False

    def handle_no_permission(self):
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.error(self.request, "No tienes permisos para acceder a RRHH.")
        return redirect('indexprueba') 
    
class SoloRRHHOGerenteMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        try:
            return u.is_authenticated and u.rol and u.rol.nombre in ['RRHH', 'Gerente']
        except Exception:
            return False
        
class RolRequiredMixin(UserPassesTestMixin):
    allowed = []  # p.ej. ['Gerente','Supervisor']
    def test_func(self):
        u = self.request.user
        try:
            return u.is_authenticated and u.rol and u.rol.nombre in self.allowed
        except Exception:
            return False

class SoloGerenteMixin(RolRequiredMixin):
    allowed = ['Gerente']

class SoloSupervisorMixin(RolRequiredMixin):
    allowed = ['Supervisor']

class SoloTrabajadorMixin(RolRequiredMixin):
    allowed = ['Trabajador']   

class SoloGerenteSupervisorMixin(RolRequiredMixin):
    allowed = ['Gerente', 'Supervisor']

     
class EmpresaContextMixin:
    """Expone self.empresa con la empresa del usuario logueado."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not getattr(request.user, "empresa_id", None):
            # sin empresa => no puede seguir
            raise PermissionDenied("Tu usuario no tiene empresa asociada.")
        self.empresa = request.user.empresa
        return super().dispatch(request, *args, **kwargs)

class EmpresaQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if not u.is_superuser and hasattr(qs.model, "empresa_id"):
            qs = qs.filter(empresa=u.empresa)
        return qs

class EmpresaObjectMixin(EmpresaQuerysetMixin):
    """
    Garantiza que get_object() también esté filtrado por empresa.
    (Al heredar de EmpresaQuerysetMixin, get_queryset ya viene filtrado).
    """
    pass

class EmpresaFormMixin:
    """Setea empresa al guardar Create/Update; asegura FK coherentes."""
    def form_valid(self, form):
        obj = form.save(commit=False)
        u = self.request.user
        if hasattr(obj, "empresa_id") and not obj.empresa_id:
            obj.empresa = u.empresa
        # Normaliza FKs con empresa del usuario si aplican
        for fk in ("departamento", "asignado", "evaluado", "evaluador", "realizado_por", "usuario"):
            if hasattr(obj, fk):
                v = getattr(obj, fk, None)
                if hasattr(v, "empresa_id") and v.empresa_id != u.empresa_id:
                    self.request._messages.error(self.request, "Objeto de otra empresa.")
                    return redirect(self.get_success_url() if hasattr(self, "get_success_url") else "/")
        obj.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()
        return super().form_valid(form)

class SuscripcionActivaRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        sub = getattr(request.user.empresa, "suscripcion", None)
        if not sub or not sub.is_active():
            messages.info(request, "Tu empresa necesita una suscripción activa para usar esta sección.")
            return redirect("billing_overview")
        return super().dispatch(request, *args, **kwargs)
