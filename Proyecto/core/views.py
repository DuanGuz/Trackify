from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from .serializers import UserSerializer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .forms import *
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy, reverse
from .models import *
from .utils import *
from django.db.models import Q, Count, Avg, Case, When, IntegerField, Sum
from .mixins import *
from django.http import HttpResponse
from django.utils.timezone import now, make_naive, localtime
from datetime import datetime
import csv
try:
    import openpyxl
except Exception:
    openpyxl = None
import json
from django.core.serializers.json import DjangoJSONEncoder
from .utils_pdf import *
from .utils_audit import *
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .utils_sms import *
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .utils_reports import *
from .utils_messages import clear_messages
from .decorators import require_gs_and_sub

import logging, json
logger = logging.getLogger(__name__)
User = get_user_model()

def _empresa_tiene_sub_activa(user) -> bool:
    sub = getattr(getattr(user, "empresa", None), "suscripcion", None)
    return bool(sub and sub.is_active())

# Create your views here.
def index(request):
	return render(request, 'core/a/index.html')

def base(request):
    return render(request, 'core/base.html')

def auth_confirm(request):
    return render(request, 'core/a/auth-confirm.html')

#LOGIN/REGISTRO WEB

#Pruebas:
def registro_web(request):
    if request.method == 'POST':
        form = RegistroRRHHForm(request.POST)
        if form.is_valid():
            user = form.save()

            # login automático
            raw_password = form.cleaned_data.get('password1')
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
                messages.success(request, "¡Cuenta creada! Completa tu suscripción para activar tu empresa.")
                return redirect('billing_checkout')  # <- manda a tu checkout
            else:
                messages.success(request, "¡Cuenta creada! Inicia sesión para continuar.")
                return redirect('web_login')

        return render(request, 'core/auth-register.html', {'form': form})
    else:
        form = RegistroRRHHForm()
    return render(request, 'core/auth-register.html', {'form': form})

'''def registro_gerente(request):
    if request.method == 'POST':
        form = RegistroRRHHForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('web_login')
    else:
        form = RegistroRRHHForm()
    return render(request, 'core/registro_gerente.html', {'form': form})'''

# Login web (Listo)
def web_login(request):
    clear_messages(request)

    if request.user.is_authenticated:
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        clear_messages(request)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            error = "Usuario o contraseña incorrectos"
    return render(request, 'core/auth-login.html', {'error': error})

# Logout web
@login_required
def web_logout(request):
    if request.method == 'POST':
        logout(request)
        next_url = request.POST.get('next') or reverse('index')
        return redirect(next_url)

# Index prueba (requiere login)
@login_required(login_url='web_login')
def indexprueba(request):
    return render(request, 'core/indexprueba.html')

# Base prueba (pública)
def baseprueba(request):
    return render(request, 'core/baseprueba.html')

#CRUD USUARIOS(RRHH):
# Listar usuarios
class UserListView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, ListView):
    model = User
    template_name = "core/usuarios/user_list.html"
    context_object_name = "usuarios"
    paginate_by = 20
    ordering = ['primer_apellido','primer_nombre']

    def get_queryset(self):
        qs = super().get_queryset().select_related('rol')
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(primer_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(rut__icontains=q) |
                Q(rol__nombre__icontains=q)
            )
        return qs
    
# Crear usuario
class RRHHUserCreateView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaFormMixin, CreateView):
    model = User
    form_class = RegistroUsuarioRRHHForm
    template_name = "core/usuarios/user_form.html"
    success_url = reverse_lazy("user_list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.user.empresa  # filtra rol/depto en el form
        return kwargs
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.empresa = self.request.user.empresa

        # Generación automática
        user.username = generate_username(user.primer_nombre, user.primer_apellido)
        user.email = generate_email(user.primer_nombre, user.primer_apellido)
        raw_password = generate_password(user.primer_nombre, user.primer_apellido, user.rut)
        user.set_password(raw_password)

        user.save()
        self.object = user  # <- clave para no invocar un segundo save interno

        messages.success(
            self.request,
            f"Usuario creado: {user.username} | Email: {user.email} | "
            f"Contraseña inicial: {raw_password} | Rol: {user.rol.nombre}"
        )
        return redirect(self.get_success_url())
    
    

    
# EDITAR
class UserUpdateView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "core/usuarios/user_form.html"
    success_url = reverse_lazy("user_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.user.empresa
        return kwargs

# ELIMINAR
class UserDeleteView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, DeleteView):
    model = User
    template_name = "core/usuarios/user_confirm_delete.html"
    success_url = reverse_lazy("user_list")

    def get(self, request, *args, **kwargs):

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj == request.user:
            messages.error(request, "No puedes eliminar tu propio usuario.")
            return redirect("user_list")
        return super().post(request, *args, **kwargs)
    
    



#CRUD DEPARTAMENTOS (RRHH):
class DepartamentoListView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, ListView):
    model = Departamento
    template_name = "core/departamentos/departamento_list.html"
    context_object_name = "departamentos"
    paginate_by = 15
    ordering = ['nombre']

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            total_tareas=Count('tarea', distinct=True),
            total_miembros=Count('miembros', distinct=True)
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        return qs

class DepartamentoCreateView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaFormMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = "core/departamentos/departamento_form.html"
    success_url = reverse_lazy("departamento_list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.user.empresa
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Departamento creado correctamente.")
        return super().form_valid(form)
    
    


class DepartamentoUpdateView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, EmpresaFormMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = "core/departamentos/departamento_form.html"
    success_url = reverse_lazy("departamento_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.user.empresa
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Departamento actualizado correctamente.")
        return super().form_valid(form)

class DepartamentoDeleteView(SuscripcionActivaRequiredMixin, SoloRRHHMixin, EmpresaQuerysetMixin, DeleteView):
    model = Departamento
    template_name = "core/departamentos/departamento_confirm_delete.html"
    success_url = reverse_lazy("departamento_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if Tarea.objects.filter(departamento=self.object, empresa=request.user.empresa).exists():
            messages.error(request, "No puedes eliminar este departamento porque tiene tareas asociadas.")
            return redirect("departamento_list")
        messages.success(request, "Departamento eliminado correctamente.")
        return super().post(request, *args, **kwargs)



#CRUD TAREAS:
# LISTAR (Gerente/Supervisor)
class TareaListGSView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_gs.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (super()
              .get_queryset()
              .select_related("departamento", "asignado")
              .order_by(*self.ordering))

        q = (self.request.GET.get("q") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()

        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) |
                Q(descripcion__icontains=q) |
                Q(asignado__primer_nombre__icontains=q) |
                Q(asignado__primer_apellido__icontains=q) |
                Q(departamento__nombre__icontains=q)
            )
        if estado:
            qs = qs.filter(estado=estado)

        user = self.request.user
        rol = getattr(getattr(user, "rol", None), "nombre", None)

        # Gerente: solo su departamento
        if rol == "Gerente" and getattr(user, "departamento_id", None):
            qs = qs.filter(departamento_id=user.departamento_id)

        # Supervisor: (si permites esta vista) mostrar equipo de su depto (trabajadores)
        if rol == "Supervisor" and getattr(user, "departamento_id", None):
            qs = qs.filter(
                asignado__rol__nombre="Trabajador",
                asignado__departamento_id=user.departamento_id
            )

        return qs

# LISTAR (Trabajador)
class TareaListTrabajadorView(SuscripcionActivaRequiredMixin, SoloTrabajadorMixin, EmpresaQuerysetMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_trab.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ['estado','fecha_limite']

    def get_queryset(self):
        return (super()
                .get_queryset()
                .filter(asignado=self.request.user)
                .select_related('departamento'))
    
# CREAR
class TareaCreateView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaFormMixin, CreateView):
    model = Tarea
    form_class = TareaForm
    template_name = "core/tareas/tarea_form.html"
    success_url = reverse_lazy("tarea_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["empresa"] = self.request.user.empresa  # <-- importante para filtrar dropdowns en el form
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.estado = "Pendiente"
        self.object.creada_por = self.request.user
        # empresa garantizada por EmpresaFormMixin, pero por si acaso:
        if not self.object.empresa_id:
            self.object.empresa = self.request.user.empresa
        self.object.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()

        HistorialTarea.objects.create(
            tarea=self.object,
            accion="CREADA",
            realizado_por=self.request.user,
            empresa=self.request.user.empresa
        )
        Notificacion.objects.create(
            usuario=self.object.asignado,
            mensaje=f"Se te asignó la tarea: {self.object.titulo}",
            empresa=self.request.user.empresa
        )
        messages.success(self.request, "Tarea creada correctamente y marcada como Pendiente.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        rol = getattr(getattr(self.request.user, "rol", None), "nombre", None)
        if rol == "Supervisor":
            return reverse("tarea_list_supervisor_equipo")
        return reverse("tarea_list_gs")


# EDITAR
class TareaUpdateView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, EmpresaFormMixin, UpdateView):
    model = Tarea
    form_class = TareaForm
    template_name = "core/tareas/tarea_form.html"
    success_url = reverse_lazy("tarea_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["empresa"] = self.request.user.empresa
        return kwargs

    def form_valid(self, form):
        original = Tarea.objects.get(pk=self.object.pk)
        # Mantener estado
        u = self.request.user
        if getattr(u, "rol", None) and u.rol.nombre in ['Gerente','Supervisor']:
            form.instance.estado = original.estado

        resp = super().form_valid(form)

        registrar_cambios_tarea(
            tarea=self.object,
            original=original,
            user=self.request.user,
            campos=['titulo', 'descripcion', 'departamento', 'asignado', 'fecha_limite']
        )
        return resp

# ELIMINAR
class TareaDeleteView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, DeleteView):
    model = Tarea
    template_name = "core/tareas/tarea_confirm_delete.html"
    success_url = reverse_lazy("tarea_list_gs")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.estado == "Finalizada":
            messages.error(request, "No puedes eliminar una tarea ya finalizada.")
            return redirect("tarea_list_gs")

        HistorialTarea.objects.create(
            tarea=obj,
            accion="ELIMINADA",
            valor_anterior=f"{obj.titulo}",
            realizado_por=request.user,
            empresa=request.user.empresa
        )
        return super().post(request, *args, **kwargs)

# DETALLE (todos los roles pueden ver si está asignado o con permisos)
class TareaDetailView(SuscripcionActivaRequiredMixin, LoginRequiredMixin, EmpresaQuerysetMixin, DetailView):
    model = Tarea
    context_object_name = "tarea"

    def _rol(self):
        r = getattr(self.request.user, "rol", None)
        return getattr(r, "nombre", None)

    def get_queryset(self):
        # 1) Filtra por empresa (mixin) y trae relaciones útiles
        qs = (super()
              .get_queryset()
              .select_related("departamento", "asignado", "asignado__rol"))
        u = self.request.user
        if u.is_superuser:
            return qs

        rol = self._rol()
        dept_id = getattr(u, "departamento_id", None)
        src = self.request.GET.get("src", "")

        # 2) Limita visibilidad por rol
        if rol == "Gerente" and dept_id:
            # Gerente: tareas del propio departamento
            return qs.filter(departamento_id=dept_id)

        if rol == "Supervisor" and dept_id:
            # Supervisor:
            # - si viene desde "mis tareas": solo las suyas
            # - si no, solo equipo (trabajadores) de su dpto
            if src == "mias":
                return qs.filter(asignado=u)
            return qs.filter(
                asignado__rol__nombre="Trabajador",
                asignado__departamento_id=dept_id
            )

        if rol == "Trabajador":
            # Trabajador: solo sus tareas
            return qs.filter(asignado=u)

        # Cualquier otro caso: no ver nada
        return qs.none()

    def get_template_names(self):
        user = self.request.user
        rol = self._rol()

        if user.is_superuser or rol == "Gerente":
            return ["core/tareas/tarea_detail_gs.html"]

        if rol == "Supervisor":
            src = self.request.GET.get("src", "")
            if src == "mias":
                return ["core/tareas/tarea_detail_supervisor_mias.html"]
            return ["core/tareas/tarea_detail_supervisor_equipo.html"]

        return ["core/tareas/tarea_detail_trab.html"]

    # === NUEVO: contexto para botón y navegación ===
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        rol = self._rol()
        obj = ctx["tarea"]

        # Solo el asignado puede cambiar estado (y nunca el Gerente)
        can_change = (obj.asignado_id == u.id) and (rol in ("Supervisor", "Trabajador"))
        ctx["can_change_state"] = can_change

        # back_url según rol/origen
        src = self.request.GET.get("src", "")
        if rol == "Supervisor":
            if src == "mias":
                back = reverse("tarea_list_supervisor_mias")
            else:
                back = reverse("tarea_list_supervisor_equipo")
        elif rol == "Trabajador":
            back = reverse("tarea_list_trab")
        elif rol == "Gerente" or u.is_superuser:
            back = reverse("tarea_list_gs")
        else:
            back = reverse("tarea_list_gs")  # fallback seguro

        # permite override con ?next=...
        ctx["back_url"] = self.request.GET.get("next", back)
        return ctx
    
# CAMBIO DE ESTADO (Trabajador)
class TareaEstadoUpdateView(LoginRequiredMixin, SuscripcionActivaRequiredMixin, EmpresaQuerysetMixin, UpdateView):
    model = Tarea
    form_class = TareaEstadoForm
    template_name = "core/tareas/tarea_estado_form.html"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()  # ← ya viene filtrado por empresa

        u = request.user
        # Gerente no cambia estados (como ya tenías)
        if getattr(u, "rol", None) and u.rol.nombre == "Gerente" and not u.is_superuser:
            messages.error(request, "El gerente no puede cambiar estados de tareas.")
            return redirect("tarea_list_gs")

        # Solo el asignado puede cambiar
        if obj.asignado_id != u.id:
            messages.error(request, "Solo el asignado puede cambiar el estado.")
            if getattr(u, "rol", None) and u.rol.nombre == "Supervisor":
                return redirect("tarea_list_supervisor_mias")
            return redirect("tarea_list_trab")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        tarea = self.get_object()
        estado_anterior = tarea.estado

        self.object = form.save(user=self.request.user)

        if estado_anterior != self.object.estado:
            HistorialTarea.objects.create(
                tarea=self.object,
                accion="ESTADO",
                campo="estado",
                valor_anterior=estado_anterior,
                valor_nuevo=self.object.estado,
                realizado_por=self.request.user,
                empresa=self.request.user.empresa
            )

        texto = (form.cleaned_data.get("comentario") or "").strip()
        if texto:
            HistorialTarea.objects.create(
                tarea=self.object,
                accion="COMENTARIO",
                campo="comentario",
                valor_nuevo=texto[:2000],
                realizado_por=self.request.user,
                empresa=self.request.user.empresa
            )

        messages.success(self.request, "Estado actualizado.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        u = self.request.user
        if getattr(u, "rol", None) and u.rol.nombre == "Supervisor":
            return reverse_lazy("tarea_list_supervisor_mias")
        return reverse_lazy("tarea_list_trab")


# EVALUACIONES:
# Listado global (Gerente ve todas; Supervisor también puede usar este con filtros si quieres)
class EvalListGSView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_gs.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        u = self.request.user
        dept_id = getattr(u.departamento, "id", None)

        qs = (super()
              .get_queryset()
              .select_related("evaluador", "evaluado", "evaluador__rol", "evaluado__rol",
                              "evaluador__departamento", "evaluado__departamento")
              .order_by(*self.ordering))

        # Visibilidad por rol
        if u.is_superuser:
            pass
        elif u.rol and u.rol.nombre == "Gerente":
            if dept_id:
                qs = qs.filter(
                    Q(tipo="SUPERVISOR", evaluado__departamento_id=dept_id) |
                    Q(tipo="TRABAJADOR", evaluador__departamento_id=dept_id)
                )
            else:
                qs = qs.none()
        elif u.rol and u.rol.nombre == "Supervisor":
            qs = qs.filter(evaluador=u)  # solo las que él realizó
        else:
            qs = qs.none()

        # Filtros
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        puntaje_min = self.request.GET.get("puntaje_min", "").strip()
        evaluador_id = self.request.GET.get("evaluador", "").strip()
        evaluado_id = self.request.GET.get("evaluado", "").strip()
        f_desde = self.request.GET.get("desde", "").strip()
        f_hasta = self.request.GET.get("hasta", "").strip()

        if q:
            qs = qs.filter(
                Q(evaluado__primer_nombre__icontains=q) |
                Q(evaluado__primer_apellido__icontains=q) |
                Q(evaluador__primer_nombre__icontains=q) |
                Q(evaluador__primer_apellido__icontains=q)
            )
        if tipo in ("SUPERVISOR", "TRABAJADOR"):
            qs = qs.filter(tipo=tipo)
        if puntaje_min.isdigit():
            qs = qs.filter(puntaje__gte=int(puntaje_min))
        if evaluador_id.isdigit():
            qs = qs.filter(evaluador_id=int(evaluador_id))
        if evaluado_id.isdigit():
            qs = qs.filter(evaluado_id=int(evaluado_id))
        if f_desde:
            qs = qs.filter(created_at__date__gte=f_desde)
        if f_hasta:
            qs = qs.filter(created_at__date__lte=f_hasta)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        dept_id = getattr(u.departamento, "id", None)

        # Selects limitados por empresa/depto
        base_users = User.objects.filter(empresa=u.empresa).select_related("rol", "departamento")

        if u.is_superuser:
            evaluadores = base_users.filter(rol__nombre__in=["Gerente", "Supervisor"]).order_by("primer_apellido","primer_nombre")
            evaluados_supervisores = base_users.filter(rol__nombre="Supervisor").order_by("primer_apellido","primer_nombre")
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador").order_by("primer_apellido","primer_nombre")
        elif u.rol and u.rol.nombre == "Gerente":
            evaluadores = base_users.filter(rol__nombre="Gerente", departamento_id=dept_id)
            evaluadores = evaluadores.union(base_users.filter(rol__nombre="Supervisor", departamento_id=dept_id)).order_by("primer_apellido","primer_nombre")
            evaluados_supervisores = base_users.filter(rol__nombre="Supervisor", departamento_id=dept_id).order_by("primer_apellido","primer_nombre")
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador", departamento_id=dept_id).order_by("primer_apellido","primer_nombre")
        else:  # Supervisor
            evaluadores = base_users.filter(id=u.id)
            evaluados_supervisores = base_users.none()
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador", departamento_id=dept_id).order_by("primer_apellido","primer_nombre")

        ctx["evaluadores"] = evaluadores
        ctx["evaluados_supervisores"] = evaluados_supervisores
        ctx["evaluados_trabajadores"] = evaluados_trabajadores

        agg = ctx["evaluaciones"].aggregate(promedio=Avg("puntaje"), total=Count("id"))
        ctx["kpi_promedio"] = agg["promedio"]
        ctx["kpi_total"] = agg["total"]
        return ctx

class EvalMisEvaluacionesView(LoginRequiredMixin, SuscripcionActivaRequiredMixin, EmpresaQuerysetMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_mias.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def dispatch(self, request, *args, **kwargs):
        # Cualquier usuario autenticado con rol válido podría ver sus propias evaluaciones
        if not request.user.is_authenticated:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        u = self.request.user
        qs = (super()
              .get_queryset()  # <--- usa el mixin
              .select_related('evaluado', 'evaluador')
              .filter(evaluado=u))
        if u.rol and u.rol.nombre == "Trabajador":
            qs = qs.filter(tipo="TRABAJADOR")
        elif u.rol and u.rol.nombre == "Supervisor":
            qs = qs.filter(tipo="SUPERVISOR")
        return qs.order_by(*self.ordering)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs_all = self.get_queryset()
        agg = qs_all.aggregate(promedio=Avg("puntaje"), total=Count("id"))
        ctx["kpi_promedio"] = agg["promedio"]
        ctx["kpi_total"] = agg["total"]
        return ctx
    
# Listado para Trabajador: solo las mías
class EvalListTrabajadorView(SuscripcionActivaRequiredMixin, SoloTrabajadorMixin, EmpresaQuerysetMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_trab.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        return (super()
                .get_queryset()  # <--- usa el mixin
                .filter(evaluado=self.request.user, tipo="TRABAJADOR")
                .select_related('evaluador')
                .order_by(*self.ordering))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs_all = (super().get_queryset()
                  .filter(evaluado=self.request.user, tipo="TRABAJADOR"))
        agg = qs_all.aggregate(promedio=Avg("puntaje"), total=Count("id"))
        ctx["kpi_promedio"] = agg["promedio"]
        ctx["kpi_total"] = agg["total"]
        return ctx

class EvalListMiasView(LoginRequiredMixin, SuscripcionActivaRequiredMixin, EmpresaQuerysetMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_mias.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        return (super()
                .get_queryset()  # <--- usa el mixin
                .filter(evaluado=self.request.user)
                .select_related('evaluador')
                .order_by(*self.ordering))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs_all = Evaluacion.objects.filter(evaluado=self.request.user)
        agg = qs_all.aggregate(promedio=Avg("puntaje"), total=Count("id"))
        ctx["kpi_promedio"] = agg["promedio"]
        ctx["kpi_total"] = agg["total"]
        return ctx
# Crear evaluación (solo Supervisor)
class EvalCreateView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaFormMixin, CreateView):
    model = Evaluacion
    form_class = EvaluacionForm
    template_name = "core/evaluaciones/eval_form.html"

    def get_success_url(self):
        return reverse("eval_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["empresa"] = self.request.user.empresa
        return kwargs

    def form_valid(self, form):
        # form ya setea evaluador y tipo en clean()
        self.object = form.save(commit=False)
        if not self.object.empresa_id:
            self.object.empresa = self.request.user.empresa
        self.object.save()

        HistorialEvaluacion.objects.create(
            evaluacion=self.object,
            accion="CREADA",
            realizado_por=self.request.user,
            empresa=self.request.user.empresa
        )
        Notificacion.objects.create(
            usuario=self.object.evaluado,
            mensaje=f"Has recibido una evaluación (puntaje {self.object.puntaje}).",
            empresa=self.request.user.empresa
        )
        messages.success(self.request, "Evaluación registrada correctamente.")
        return redirect(self.get_success_url())

# Editar evaluación (solo quien la creó o Gerente)
class EvalGeneralUpdateView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, EmpresaFormMixin, UpdateView):
    model = Evaluacion
    form_class = EvaluacionForm
    template_name = "core/evaluaciones/eval_form.html"

    def get_success_url(self):
        return reverse_lazy("eval_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["empresa"] = self.request.user.empresa
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        u = request.user

        if u.rol and u.rol.nombre == "Supervisor" and obj.evaluador != u and not u.is_superuser:
            messages.error(request, "Solo puedes editar evaluaciones creadas por ti.")
            return redirect("eval_list_gs")

        if u.rol and u.rol.nombre == "Gerente" and not u.is_superuser:
            same = (getattr(u, "departamento_id", None) ==
                    getattr(obj.evaluador, "departamento_id", None) ==
                    getattr(obj.evaluado, "departamento_id", None))
            if not same:
                messages.error(request, "No puedes editar evaluaciones fuera de tu departamento.")
                return redirect("eval_list_gs")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        original = Evaluacion.objects.get(pk=self.object.pk)
        self.object = form.save()

        Notificacion.objects.create(
            usuario=self.object.evaluado,
            mensaje=f"Tu evaluación fue actualizada (puntaje {self.object.puntaje}).",
            empresa=self.request.user.empresa
        )
        messages.success(self.request, "Evaluación actualizada.")
        return redirect(self.get_success_url())

# Eliminar evaluación (autor o Gerente)
class EvalGeneralDeleteView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, DeleteView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_confirm_delete.html"
    success_url = reverse_lazy("eval_list_gs")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        u = request.user

        if u.rol and u.rol.nombre == "Supervisor" and obj.evaluador != u and not u.is_superuser:
            messages.error(request, "Solo puedes eliminar evaluaciones creadas por ti.")
            return redirect("eval_list_gs")

        if u.rol and u.rol.nombre == "Gerente" and not u.is_superuser:
            same = (getattr(u, "departamento_id", None) ==
                    getattr(obj.evaluador, "departamento_id", None) ==
                    getattr(obj.evaluado, "departamento_id", None))
            if not same:
                messages.error(request, "No puedes eliminar evaluaciones fuera de tu departamento.")
                return redirect("eval_list_gs")

        messages.success(request, "Evaluación eliminada.")
        return super().post(request, *args, **kwargs)

# DASHBOARD/REPORTES:
class DashboardView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        rn = getattr(getattr(u, "rol", None), "nombre", "")
        depto = getattr(u, "departamento", None)

        # Bases por empresa
        qs_users  = User.objects.select_related("rol", "departamento").filter(empresa=u.empresa)
        qs_tareas = (Tarea.objects
                     .select_related("departamento", "asignado", "asignado__rol")
                     .filter(empresa=u.empresa))
        qs_eval   = (Evaluacion.objects
                     .select_related("evaluado", "evaluador",
                                     "evaluado__rol", "evaluado__departamento",
                                     "evaluador__rol", "evaluador__departamento")
                     .filter(empresa=u.empresa))

        # Alcance por rol
        if u.is_superuser:
            pass
        elif rn == "Gerente" and depto:
            qs_users  = qs_users.filter(departamento=depto)
            qs_tareas = qs_tareas.filter(departamento=depto)  # Gerente ve tareas de Supervisores + Trabajadores de su depto
            qs_eval   = qs_eval.filter(evaluado__departamento=depto)
        elif rn == "Supervisor" and depto:
            qs_users  = qs_users.filter(departamento=depto, rol__nombre="Trabajador")
            qs_tareas = qs_tareas.filter(departamento=depto, asignado__rol__nombre="Trabajador")  # solo trabajadores
            qs_eval   = qs_eval.filter(tipo="TRABAJADOR", evaluado__departamento=depto, evaluado__rol__nombre="Trabajador")

        # ===== Gráfico principal: Tareas por estado (barras múltiples por rol asignado)
        ESTADOS = ["Pendiente", "En progreso", "Atrasada", "Finalizada"]
        agg_estado_rol = qs_tareas.values("estado", "asignado__rol__nombre").annotate(total=Count("id"))
        por_estado = {e: {"Trabajador": 0, "Supervisor": 0} for e in ESTADOS}
        for row in agg_estado_rol:
            est = row["estado"]
            rol_asig = row["asignado__rol__nombre"] or ""
            if est in por_estado and rol_asig in por_estado[est]:
                por_estado[est][rol_asig] = row["total"]

        data_trab = [por_estado[e]["Trabajador"] for e in ESTADOS]
        data_supv = [por_estado[e]["Supervisor"] for e in ESTADOS]  # para Supervisor quedará en 0 (OK)

        # KPIs y tablas
        usuarios_por_rol = qs_users.values("rol__nombre").annotate(total=Count("id")).order_by("rol__nombre")
        atrasadas = qs_tareas.filter(estado="Atrasada").count()

        # Top 5
        top_n = 5
        top_trabajadores = (qs_eval.filter(evaluado__rol__nombre="Trabajador")
                            .values("evaluado__primer_nombre","evaluado__primer_apellido")
                            .annotate(prom=Avg("puntaje"), total=Count("id"))
                            .order_by("-prom","-total")[:top_n])

        top_supervisores = (qs_eval.filter(evaluado__rol__nombre="Supervisor")
                            .values("evaluado__primer_nombre","evaluado__primer_apellido")
                            .annotate(prom=Avg("puntaje"), total=Count("id"))
                            .order_by("-prom","-total")[:top_n])

        # Tabla por estado (desglose por rol si aplica)
        tabla_estado = []
        for e in ESTADOS:
            fila = {
                "estado": e,
                "trab": por_estado[e]["Trabajador"],
                "sup": por_estado[e]["Supervisor"],
            }
            fila["total"] = fila["trab"] + fila["sup"]
            tabla_estado.append(fila)

        ctx.update({
            "role_name": rn,
            "estados_labels": ESTADOS,
            "tareas_estado_trab": data_trab,
            "tareas_estado_sup": data_supv,
            "tareas_atrasadas": atrasadas,

            "usuarios_por_rol": usuarios_por_rol,  # se mostrará solo a Gerente/SU
            "tabla_estado": tabla_estado,

            "top_trabajadores": top_trabajadores,   # top 5
            "top_supervisores": top_supervisores,   # top 5 (solo Gerente/SU)
        })
        return ctx
    

# -----------------------
# Helpers de filtros comunes
# -----------------------
def parse_fecha(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def filtrar_tareas(request):
    qs = (Tarea.objects
          .select_related("departamento","asignado")
          .filter(empresa=request.user.empresa))  # ← clave

    estado = request.GET.get("estado","").strip()
    depto = request.GET.get("depto","").strip()
    asignado = request.GET.get("asignado","").strip()
    f_ini = parse_fecha(request.GET.get("f_ini",""))
    f_fin = parse_fecha(request.GET.get("f_fin",""))

    if estado:
        qs = qs.filter(estado=estado)

    # Solo superuser puede cambiar depto en GET; otros quedan en su depto
    if depto and request.user.is_superuser:
        qs = qs.filter(departamento_id=depto)

    if asignado:
        qs = qs.filter(asignado_id=asignado)
    if f_ini:
        qs = qs.filter(fecha_limite__gte=f_ini)
    if f_fin:
        qs = qs.filter(fecha_limite__lte=f_fin)
    return qs

def filtrar_evaluaciones(request):
    qs = (Evaluacion.objects
          .select_related('evaluado', 'evaluador')
          .filter(empresa=request.user.empresa))  # ← clave

    q = (request.GET.get("q") or "").strip()
    tipo = (request.GET.get("tipo") or "").strip()
    evaluador_id = request.GET.get("evaluador") or ""
    evaluado_id = request.GET.get("evaluado") or ""
    f_desde = request.GET.get("desde") or ""
    f_hasta = request.GET.get("hasta") or ""
    puntaje_min = request.GET.get("puntaje_min") or ""

    if q:
        qs = qs.filter(
            Q(evaluado__primer_nombre__icontains=q) |
            Q(evaluado__primer_apellido__icontains=q) |
            Q(evaluador__primer_nombre__icontains=q) |
            Q(evaluador__primer_apellido__icontains=q)
        )
    if tipo in ("SUPERVISOR", "TRABAJADOR"):
        qs = qs.filter(tipo=tipo)
    if evaluador_id.isdigit():
        qs = qs.filter(evaluador_id=int(evaluador_id))
    if evaluado_id.isdigit():
        qs = qs.filter(evaluado_id=int(evaluado_id))
    if f_desde:
        qs = qs.filter(created_at__date__gte=f_desde)
    if f_hasta:
        qs = qs.filter(created_at__date__lte=f_hasta)
    if puntaje_min:
        try:
            qs = qs.filter(puntaje__gte=int(puntaje_min))
        except ValueError:
            pass

    # Visibilidad adicional por rol (opcional)
    u = request.user
    rol = getattr(getattr(u, "rol", None), "nombre", "")
    if rol == "Supervisor" and not u.is_superuser:
        qs = qs.filter(evaluador=u)
    # Si quieres restringir Gerente a su depto:
    # if rol == "Gerente" and u.departamento_id:
    #     qs = qs.filter(evaluado__departamento_id=u.departamento_id)

    return qs
# -----------------------
# REPORTES TAREAS (lista + filtros)
# -----------------------
def _rol(user):
    return getattr(getattr(user, "rol", None), "nombre", "")

def _dept(user):
    return getattr(user, "departamento", None)

def _users_en_depto(role_name, dept):
    return User.objects.filter(rol__nombre=role_name, departamento=dept, empresa=dept.empresa)

class ReporteTareasView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/reportes/reporte_tareas.html"

    def get_queryset(self):
        u = self.request.user
        su = u.is_superuser
        rol = _rol(u)
        dept = _dept(u)

        qs = (Tarea.objects
              .select_related("departamento", "asignado", "asignado__rol")
              .filter(empresa=u.empresa))  # ← clave

        if not su:
            qs = qs.filter(departamento=dept)
            if rol == "Supervisor":
                qs = qs.filter(asignado__rol__nombre="Trabajador", asignado__departamento=dept)

        # Filtros GET
        estado = self.request.GET.get("estado", "").strip()
        depto = self.request.GET.get("depto", "").strip()
        asignado_id = self.request.GET.get("asignado", "").strip()
        f_ini = self.request.GET.get("f_ini", "").strip()
        f_fin = self.request.GET.get("f_fin", "").strip()

        if estado in ("Pendiente", "En progreso", "Atrasada", "Finalizada"):
            qs = qs.filter(estado=estado)

        if depto.isdigit() and su:
            qs = qs.filter(departamento_id=int(depto))

        if asignado_id.isdigit():
            qs = qs.filter(asignado_id=int(asignado_id))

        if f_ini:
            qs = qs.filter(fecha_limite__gte=f_ini)
        if f_fin:
            qs = qs.filter(fecha_limite__lte=f_fin)

        return qs.order_by("fecha_limite")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        su = u.is_superuser
        rol = _rol(u)
        dept = _dept(u)

        qs = self.get_queryset()

        # Listas de filtro (limitadas por empresa)
        if su:
            departamentos = Departamento.objects.filter(empresa=u.empresa).order_by("nombre")
            asignables = User.objects.filter(empresa=u.empresa).exclude(rol__nombre="Recursos humanos").order_by("primer_apellido")
        elif rol == "Gerente":
            departamentos = Departamento.objects.filter(empresa=u.empresa, pk=getattr(dept, "pk", None))
            asignables = User.objects.filter(empresa=u.empresa, departamento=dept, rol__nombre__in=["Supervisor","Trabajador"]).order_by("primer_apellido")
        else:  # Supervisor
            departamentos = Departamento.objects.filter(empresa=u.empresa, pk=getattr(dept, "pk", None))
            asignables = User.objects.filter(empresa=u.empresa, departamento=dept, rol__nombre="Trabajador").order_by("primer_apellido")

        total = qs.count()
        pend = qs.filter(estado="Pendiente").count()
        prog = qs.filter(estado="En progreso").count()
        atras = qs.filter(estado="Atrasada").count()
        fin = qs.filter(estado="Finalizada").count()

        def pct(n, d): return (n * 100.0 / d) if d else 0.0

        ctx.update({
            "tareas": qs,
            "departamentos": departamentos,
            "trabajadores": asignables,
            "kpi_total": total,
            "kpi_pend": pend, "kpi_pend_pct": pct(pend, total),
            "kpi_prog": prog, "kpi_prog_pct": pct(prog, total),
            "kpi_atras": atras, "kpi_atras_pct": pct(atras, total),
            "kpi_fin": fin, "kpi_fin_pct": pct(fin, total),
        })
        return ctx

@login_required
@require_gs_and_sub
def exportar_tareas_csv(request):
    qs = filtrar_tareas(request).filter(empresa=request.user.empresa).order_by("fecha_limite","estado")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reporte_tareas.csv"'
    writer = csv.writer(response)
    writer.writerow(["Título","Departamento","Asignado","Estado","Vence"])
    for t in qs:
        writer.writerow([
            t.titulo,
            t.departamento.nombre if t.departamento else "",
            f"{t.asignado.primer_nombre} {t.asignado.primer_apellido}" if t.asignado else "",
            t.estado,
            t.fecha_limite.strftime("%Y-%m-%d") if t.fecha_limite else ""
        ])
    return response

@login_required
@require_gs_and_sub
def exportar_tareas_xlsx(request):
    qs = filtrar_tareas(request).filter(empresa=request.user.empresa).order_by("fecha_limite","estado")
    if openpyxl is None:
        return HttpResponse("openpyxl no está instalado. Instala con: pip install openpyxl", status=500)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Tareas"
    ws.append(["Título","Departamento","Asignado","Estado","Vence"])
    for t in qs:
        ws.append([
            t.titulo,
            t.departamento.nombre if t.departamento else "",
            f"{t.asignado.primer_nombre} {t.asignado.primer_apellido}" if t.asignado else "",
            t.estado,
            t.fecha_limite.strftime("%Y-%m-%d") if t.fecha_limite else ""
        ])
    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = 'attachment; filename="reporte_tareas.xlsx"'
    return resp
# Exportar TAREAS a PDF

@login_required
@require_gs_and_sub
def exportar_tareas_pdf(request):
    qs = filtrar_tareas(request).filter(empresa=request.user.empresa).order_by("fecha_limite","estado")
    context = {
        "tareas": qs,
        "filtros": request.GET,  # por si quieres mostrar filtros aplicados
        "titulo": "Tareas",
        "now": now(),
    }
    return render_to_pdf("core/reportes/pdf_tareas.html", context, filename="reporte_tareas.pdf")

# -----------------------
# REPORTES EVALUACIONES
# -----------------------

class ReporteEvaluacionesView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/reportes/reporte_evaluaciones.html"

    def get_queryset(self):
        u = self.request.user
        su = u.is_superuser
        rol = _rol(u)
        dept = _dept(u)

        qs = (Evaluacion.objects
              .select_related("evaluado", "evaluador", "evaluado__rol", "evaluador__rol")
              .filter(empresa=u.empresa))  # ← clave

        if not su:
            qs = qs.filter(evaluado__departamento=dept, evaluador__departamento=dept)
            if rol == "Supervisor":
                qs = qs.filter(tipo="TRABAJADOR", evaluador=u)

        # Filtros GET (igual que antes)
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        puntaje_min = self.request.GET.get("puntaje_min", "").strip()
        evaluador_id = self.request.GET.get("evaluador", "").strip()
        evaluado_id = self.request.GET.get("evaluado", "").strip()
        f_desde = self.request.GET.get("desde", "").strip()
        f_hasta = self.request.GET.get("hasta", "").strip()

        if q:
            qs = qs.filter(
                Q(evaluado__primer_nombre__icontains=q) |
                Q(evaluado__primer_apellido__icontains=q) |
                Q(evaluador__primer_nombre__icontains=q) |
                Q(evaluador__primer_apellido__icontains=q)
            )
        if tipo in ("SUPERVISOR", "TRABAJADOR"):
            qs = qs.filter(tipo=tipo)
        if puntaje_min.isdigit():
            qs = qs.filter(puntaje__gte=int(puntaje_min))
        if evaluador_id.isdigit():
            qs = qs.filter(evaluador_id=int(evaluador_id))
        if evaluado_id.isdigit():
            qs = qs.filter(evaluado_id=int(evaluado_id))
        if f_desde:
            qs = qs.filter(created_at__date__gte=f_desde)
        if f_hasta:
            qs = qs.filter(created_at__date__lte=f_hasta)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        su = u.is_superuser
        rol = _rol(u)
        dept = _dept(u)
        base_users = User.objects.filter(empresa=u.empresa)

        qs = self.get_queryset()

        if su:
            evaluadores = base_users.filter(rol__nombre__in=["Gerente","Supervisor"]).order_by("primer_apellido")
            evaluados_supervisores = base_users.filter(rol__nombre="Supervisor").order_by("primer_apellido")
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador").order_by("primer_apellido")
        elif rol == "Gerente":
            evaluadores = base_users.filter(
                Q(rol__nombre="Gerente", departamento=dept) |
                Q(rol__nombre="Supervisor", departamento=dept)
            ).order_by("primer_apellido")
            evaluados_supervisores = base_users.filter(rol__nombre="Supervisor", departamento=dept).order_by("primer_apellido")
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador", departamento=dept).order_by("primer_apellido")
        else:
            evaluadores = base_users.filter(pk=u.pk)
            evaluados_supervisores = base_users.none()
            evaluados_trabajadores = base_users.filter(rol__nombre="Trabajador", departamento=dept).order_by("primer_apellido")

        agg = qs.aggregate(promedio=Avg("puntaje"), total=Count("id"))
        resumen = (qs.values("evaluado__primer_nombre", "evaluado__primer_apellido", "evaluado__rol__nombre")
                     .annotate(prom=Avg("puntaje"), total=Count("id"))
                     .order_by("-prom","-total"))

        ctx.update({
            "evaluaciones": qs,
            "kpi_promedio": agg["promedio"],
            "kpi_total": agg["total"],
            "evaluadores": evaluadores,
            "evaluados_supervisores": evaluados_supervisores,
            "evaluados_trabajadores": evaluados_trabajadores,
            "resumen_evaluados": resumen,
        })
        return ctx

def filtrar_evals(request):
    qs = (Evaluacion.objects
          .select_related('evaluado__rol', 'evaluador__rol')
          .filter(empresa=request.user.empresa))

    q = (request.GET.get("q") or "").strip()
    tipo = request.GET.get("tipo") or ""
    puntaje_min = request.GET.get("puntaje_min") or ""
    evaluador_id = request.GET.get("evaluador") or ""
    evaluado_id = request.GET.get("evaluado") or ""
    f_desde = request.GET.get("desde") or ""
    f_hasta = request.GET.get("hasta") or ""

    if q:
        qs = qs.filter(
            Q(evaluado__primer_nombre__icontains=q) |
            Q(evaluado__primer_apellido__icontains=q) |
            Q(evaluador__primer_nombre__icontains=q) |
            Q(evaluador__primer_apellido__icontains=q)
        )
    if tipo in ("SUPERVISOR", "TRABAJADOR"):
        qs = qs.filter(tipo=tipo)
    if puntaje_min:
        try:
            qs = qs.filter(puntaje__gte=int(puntaje_min))
        except ValueError:
            pass
    if evaluador_id:
        qs = qs.filter(evaluador_id=evaluador_id)
    if evaluado_id:
        qs = qs.filter(evaluado_id=evaluado_id)
    if f_desde:
        qs = qs.filter(created_at__date__gte=f_desde)
    if f_hasta:
        qs = qs.filter(created_at__date__lte=f_hasta)

    return qs

@login_required
@require_gs_and_sub
def exportar_evals_csv(request):
    qs = filtrar_evaluaciones(request).order_by("-created_at")  # ya filtra por empresa
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="reporte_evaluaciones.csv"'
    writer = csv.writer(response)
    writer.writerow(["Evaluado","Tipo","Evaluador","Puntaje","Fecha","Comentarios"])
    for e in qs:
        evaluado = f"{getattr(e.evaluado,'primer_nombre','')} {getattr(e.evaluado,'primer_apellido','')}".strip()
        evaluador = f"{getattr(e.evaluador,'primer_nombre','')} {getattr(e.evaluador,'primer_apellido','')}".strip()
        tipo = "Supervisor" if e.tipo == "SUPERVISOR" else "Trabajador"
        writer.writerow([
            evaluado,
            tipo,
            evaluador,
            e.puntaje,
            localtime(e.created_at).strftime("%Y-%m-%d %H:%M"),
            (e.comentarios or "").replace("\n"," ").strip()
        ])
    return response

@login_required
@require_gs_and_sub
def exportar_evals_xlsx(request):
    qs = filtrar_evals(request).filter(empresa=request.user.empresa).order_by("-created_at")

    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("openpyxl no está instalado. Instala con: pip install openpyxl", status=500)

    wb = Workbook()
    ws = wb.active
    ws.title = "Evaluaciones"

    # Encabezados
    ws.append(["Evaluado", "Tipo", "Evaluador", "Puntaje", "Fecha", "Comentarios"])

    # Filas
    for e in qs:
        evaluado = f"{getattr(e.evaluado, 'primer_nombre', '')} {getattr(e.evaluado, 'primer_apellido', '')}".strip()
        evaluador = f"{getattr(e.evaluador, 'primer_nombre', '')} {getattr(e.evaluador, 'primer_apellido', '')}".strip()
        tipo = "Supervisor" if e.tipo == "SUPERVISOR" else "Trabajador"
        fecha = localtime(e.created_at).strftime("%Y-%m-%d %H:%M")
        ws.append([
            evaluado,
            tipo,
            evaluador,
            e.puntaje,
            fecha,
            e.comentarios or ""
        ])

    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = f'attachment; filename="reporte_evaluaciones_{now().strftime("%Y%m%d_%H%M")}.xlsx"'
    return resp

# Exportar EVALUACIONES a PDF
@login_required
@require_gs_and_sub
def exportar_evals_pdf(request):
    qs = filtrar_evaluaciones(request).filter(empresa=request.user.empresa).order_by("-created_at")
    context = {
        "evaluaciones": qs,
        "filtros": request.GET,
        "titulo": "Evaluaciones",
        "now": now(),
    }
    return render_to_pdf("core/reportes/pdf_evaluaciones.html", context, filename="reporte_evaluaciones.pdf")

def pdfbase(request):
    return render(request, 'core/reportes/pdf_base.html')

# HISTORIAL DE CAMBIOS (solo Gerente/Supervisor):
class TareaHistorialView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, DetailView):
    model = Tarea
    template_name = "core/tareas/tarea_historial.html"
    context_object_name = "tarea"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = self.object.historial.select_related("realizado_por")
        return ctx

class EvalHistorialView(SuscripcionActivaRequiredMixin, SoloGerenteSupervisorMixin, EmpresaQuerysetMixin, DetailView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_historial.html"
    context_object_name = "evaluacion"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = self.object.historial.select_related("realizado_por")
        return ctx

# PERFIL Y CAMBIO DE PASSWORD:
class PerfilView(LoginRequiredMixin, DetailView):
    template_name = "core/perfil/perfil_detail.html"
    context_object_name = "usuario"

    def get_object(self):
        return self.request.user


class PerfilUpdateView(LoginRequiredMixin, UpdateView):
    form_class = PerfilForm
    template_name = "core/perfil/perfil_form.html"
    success_url = reverse_lazy("perfil")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Perfil actualizado correctamente.")
        return super().form_valid(form)


class MiPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "core/perfil/password_change.html"  # tu template
    success_url = reverse_lazy("perfil")
    form_class = PerfilSetPasswordForm  # ← clave: usamos SetPasswordForm personalizado

    def get_form_kwargs(self):
        # PasswordChangeView ya inyecta user, pero lo explicitamos
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Guardar nueva contraseña SIN pedir la antigua
        user = form.save()
        # Mantener la sesión activa después del cambio
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Contraseña actualizada.")
        return super().form_valid(form)

@login_required
def home(request):
    u = request.user
    rol = getattr(getattr(u, "rol", None), "nombre", "")
    # Superuser: ignora suscripción; resto: evalúa
    suscripcion_activa = True if u.is_superuser else _empresa_tiene_sub_activa(u)

    # Si la suscripción NO está activa:
    if not u.is_superuser and not suscripcion_activa:
        if rol in ("Recursos humanos", "Gerente"):
            # Solo RRHH / Gerente deben ir a pagar
            messages.info(request, "Tu empresa necesita una suscripción activa para usar la app. Completa el pago aquí.")
            return redirect("billing_checkout")
        else:
            # Trabajador / Supervisor: NO redirigir a checkout, solo avisar
            messages.info(request, "Tu empresa no tiene una suscripción activa. Contacta a tu Gerente o RRHH.")

    ctx = {
        "suscripcion_activa": suscripcion_activa,
        "role_name": rol,
    }

    # ===== Bases por empresa (o global si es superuser) =====
    users_qs = User.objects.all() if u.is_superuser else User.objects.filter(empresa=u.empresa)
    depto_qs = Departamento.objects.all() if u.is_superuser else Departamento.objects.filter(empresa=u.empresa)
    tareas_qs = Tarea.objects.all() if u.is_superuser else Tarea.objects.filter(empresa=u.empresa)

    # --- RRHH: contadores y últimos usuarios ---
    if u.is_superuser or rol == "Recursos humanos":
        ctx["usuarios_count"] = users_qs.count()
        ctx["departamentos_count"] = depto_qs.count()
        ctx["ultimos_usuarios"] = users_qs.select_related("rol").order_by("-created_at")[:8]

    # --- Gerente / Supervisor: métricas del DEPARTAMENTO del usuario ---
    if u.is_superuser or rol in ("Gerente", "Supervisor"):
        base_qs = tareas_qs.select_related("departamento", "asignado")
        if rol in ("Gerente", "Supervisor") and u.departamento_id:
            base_qs = base_qs.filter(departamento_id=u.departamento_id)

        ctx["tareas_total_count"] = base_qs.count()
        ctx["tareas_atrasadas_count"] = base_qs.filter(estado="Atrasada").count()
        ctx["tareas_en_progreso_count"] = base_qs.filter(estado="En progreso").count()
        ctx["tareas_recent"] = base_qs.order_by("-created_at")[:8]

    # --- Trabajador: sus propias tareas ---
    if u.is_superuser or rol == "Trabajador":
        mis_qs = tareas_qs.filter(asignado=u).select_related("departamento")
        ctx["mis_tareas_pendientes_count"] = mis_qs.filter(estado="Pendiente").count()
        ctx["mis_tareas"] = mis_qs.order_by("fecha_limite")[:10]

    return render(request, "core/home.html", ctx)

def _normaliza_rut(rut: str) -> str:
    # muy básico; reemplaza con tu validador real si lo tienes
    return rut.replace(".", "").replace("-", "").upper()

def password_reset_sms_request(request):
    """
    Paso 1: el usuario pide código (por RUT/username/teléfono)
    """
    if request.method == "POST":
        form = SMSRequestForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data["identificador"].strip()

            # Buscar usuario por RUT, username o teléfono
            user = None
            # intenta RUT
            try:
                user = User.objects.get(rut=_normaliza_rut(ident))
            except User.DoesNotExist:
                # intenta username
                try:
                    user = User.objects.get(username__iexact=ident)
                except User.DoesNotExist:
                    # intenta teléfono
                    try:
                        user = User.objects.get(telefono=ident)
                    except User.DoesNotExist:
                        pass

            if not user or not user.telefono:
                messages.error(request, "No se encontró un usuario con esos datos o no tiene teléfono asociado.")
                return redirect("password_reset_sms_request")

            # Rate limit
            ip = request.META.get("REMOTE_ADDR")
            if not check_rate_limit(user.telefono, ip):
                messages.error(request, "Has superado el límite de intentos. Intenta más tarde.")
                return redirect("password_reset_sms_request")

            # Crear OTP
            reset_obj, code = crear_reset_sms(user)
            # Enviar SMS
            ok, err = send_sms(user.telefono, f"Tu código de recuperación es: {code}. Expira en 10 minutos.")
            if not ok:
                messages.error(request, f"No se pudo enviar el SMS: {err or 'Error desconocido'}")
                return redirect("password_reset_sms_request")

            # Guardar id en sesión para continuar a verificación
            request.session["reset_sms_id"] = reset_obj.id
            messages.success(request, f"Te enviamos un código al {user.telefono[-4:].rjust(len(user.telefono), '*')}.")
            return redirect("password_reset_sms_verify")
    else:
        form = SMSRequestForm()

    return render(request, "core/auth/password_reset_sms_request.html", {"form": form})


def password_reset_sms_verify_code(request):
    """
    Paso 2 (nuevo): el usuario ingresa SOLO el código.
    Si es válido, marcamos la verificación en sesión y redirigimos a cambiar contraseña.
    """
    reset_id = request.session.get("reset_sms_id")
    if not reset_id:
        messages.error(request, "Sesión de recuperación no encontrada. Solicita un nuevo código.")
        return redirect("password_reset_sms_request")

    reset_obj = get_object_or_404(PasswordResetSMS, id=reset_id)

    # Expirado o usado → volver a pedir
    if reset_obj.used or reset_obj.is_expired():
        messages.error(request, "El código expiró o ya fue utilizado. Solicita uno nuevo.")
        request.session.pop("reset_sms_id", None)
        return redirect("password_reset_sms_request")

    tel = reset_obj.telefono or getattr(getattr(reset_obj, "user", None), "telefono", "")
    phone_hint = tel[-4:].rjust(len(tel), "*") if tel else ""

    if request.method == "POST":
        form = SMSCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()

            if not reset_obj.can_attempt():
                messages.error(request, "Se superó el número de intentos permitidos.")
                request.session.pop("reset_sms_id", None)
                return redirect("password_reset_sms_request")

            if not verificar_otp(reset_obj, code):
                remaining = max(reset_obj.max_intentos - reset_obj.intentos, 0)
                messages.error(request, f"Código inválido. Intentos restantes: {remaining}")
                return render(request, "core/auth/password_reset_sms_verify_code.html", {
                    "form": form,
                    "phone_hint": phone_hint,
                })

            # Código OK: marcamos verificación y redirigimos al cambio de contraseña
            request.session["reset_sms_verified"] = True
            return redirect("password_reset_sms_change")
    else:
        form = SMSCodeForm()

    return render(request, "core/auth/password_reset_sms_verify_code.html", {
        "form": form,
        "phone_hint": phone_hint,
    })


def password_reset_sms_change(request):
    """
    Paso 3 (nuevo): solo cambiar contraseña. Requiere verificación previa en sesión.
    """
    reset_id = request.session.get("reset_sms_id")
    verified = request.session.get("reset_sms_verified", False)

    if not reset_id or not verified:
        messages.error(request, "Primero debes verificar el código.")
        return redirect("password_reset_sms_request")

    reset_obj = get_object_or_404(PasswordResetSMS, id=reset_id)

    # Seguridad extra
    if reset_obj.used or reset_obj.is_expired():
        messages.error(request, "El enlace expiró o ya fue utilizado. Solicita un nuevo código.")
        # limpiar sesión
        request.session.pop("reset_sms_id", None)
        request.session.pop("reset_sms_verified", None)
        return redirect("password_reset_sms_request")

    if request.method == "POST":
        form = SMSChangePasswordForm(request.POST)
        if form.is_valid():
            user = reset_obj.user
            user.set_password(form.cleaned_data["new_password1"])
            user.save()
            reset_obj.used = True
            reset_obj.save(update_fields=["used"])

            # limpiar sesión
            request.session.pop("reset_sms_id", None)
            request.session.pop("reset_sms_verified", None)

            messages.success(request, "Tu contraseña fue actualizada. Ahora puedes iniciar sesión.")
            return redirect("inicio")
    else:
        form = SMSChangePasswordForm()

    return render(request, "core/auth/password_reset_sms_change.html", {
        "form": form,
    })

#Notificaciones:
@login_required
def notif_list_api(request):
    """
    Devuelve las notificaciones del usuario logueado.
    """
    qs = (Notificacion.objects
          .filter(usuario=request.user)
          .order_by('-created_at')[:100])

    data = []
    unread = 0
    for n in qs:
        if not n.is_read:
            unread += 1
        data.append({
            "id": n.id,
            "mensaje": n.mensaje,
            "is_read": n.is_read,
            "created_at": localtime(n.created_at).strftime("%d/%m/%Y %H:%M"),
        })
    return JsonResponse({"items": data, "unread_count": unread})

@login_required
@require_POST
def notif_clear_api(request):
    """
    Marca como leídas todas las notificaciones del usuario.
    """
    Notificacion.objects.filter(usuario=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def notif_delete_all_api(request):
    """
    Elimina todas las notificaciones del usuario.
    """
    Notificacion.objects.filter(usuario=request.user).delete()
    return JsonResponse({"ok": True})

@login_required
@require_gs_and_sub
def api_usuarios_por_rol_y_depto(request):
    rol = request.GET.get('rol')  # "Supervisor" o "Trabajador"
    depto_id = request.GET.get('depto')

    qs = User.objects.filter(empresa=request.user.empresa)
    if rol:
        qs = qs.filter(rol__nombre=rol)
    if depto_id:
        qs = qs.filter(departamento_id=depto_id)

    items = [
        {"id": u.id, "text": f"{u.primer_nombre} {u.primer_apellido}"}
        for u in qs.order_by('primer_apellido','primer_nombre')
    ]
    return JsonResponse({"items": items})

class TareaListSupervisorMiasView(SuscripcionActivaRequiredMixin, SoloSupervisorMixin, EmpresaQuerysetMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_supervisor_mias.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ["fecha_limite", "titulo"]

    def get_queryset(self):
        qs = (super()
              .get_queryset()  # <--- usa el mixin
              .filter(asignado=self.request.user)
              .select_related("departamento", "asignado"))

        q = (self.request.GET.get("q") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()

        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) |
                Q(descripcion__icontains=q)
            )

        if estado:
            qs = qs.filter(estado=estado)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ESTADOS"] = ["Pendiente", "En progreso", "Atrasada", "Finalizada"]
        return ctx
    
class TareaListSupervisorEquipoView(SuscripcionActivaRequiredMixin, SoloSupervisorMixin, EmpresaQuerysetMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_supervisor_equipo.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = (super()
              .get_queryset()  # <--- usa el mixin
              .select_related("departamento", "asignado")
              .filter(
                  asignado__rol__nombre="Trabajador",
                  asignado__departamento=user.departamento
              ))

        # Filtros opcionales
        q = (self.request.GET.get("q") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()

        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(descripcion__icontains=q))
        if estado:
            qs = qs.filter(estado=estado)

        return qs.order_by(*self.ordering)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ESTADOS"] = ["Pendiente", "En progreso", "Atrasada", "Finalizada"]
        return ctx
    
