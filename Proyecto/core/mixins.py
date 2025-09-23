from django.contrib.auth.mixins import UserPassesTestMixin

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

     



