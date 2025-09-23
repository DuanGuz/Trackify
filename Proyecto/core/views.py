from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout, get_user_model
from .serializers import UserSerializer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import *
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from .models import *
from .utils import *
from django.db.models import Q, Count, Avg
from .mixins import *
from django.http import HttpResponse
from django.utils.timezone import now
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

User = get_user_model()

# Create your views here.
def index(request):
	return render(request, 'core/index.html')

def base(request):
    return render(request, 'core/base.html')

def auth_confirm(request):
    return render(request, 'core/auth-confirm.html')

def profile(request):
    return render(request, 'core/profile.html')





#LOGIN/REGISTRO WEB
def registro_gerente(request):
    if request.method == 'POST':
        form = RegistroGerenteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('web_login')
    else:
        form = RegistroGerenteForm()
    return render(request, 'core/registro_gerente.html', {'form': form})

# Login web
def web_login(request):
    if request.user.is_authenticated:
        return redirect('user_list')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('user_list')
        else:
            error = "Usuario o contraseña incorrectos"
    return render(request, 'core/pruebalogin.html', {'error': error})

# Logout web
def web_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('baseprueba')
    return redirect('indexprueba')

# Index prueba (requiere login)
@login_required(login_url='web_login')
def indexprueba(request):
    return render(request, 'core/indexprueba.html')

# Base prueba (pública)
def baseprueba(request):
    return render(request, 'core/baseprueba.html')


#CRUD USUARIOS(RRHH):
# Listar usuarios
class UserListView(ListView):
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
class RRHHUserCreateView(CreateView):
    model = User
    form_class = RegistroUsuarioRRHHForm
    template_name = "core/usuarios/user_form.html"
    success_url = reverse_lazy("user_list")

    def form_valid(self, form):
        user = form.save(commit=False)

        # Generación automática
        user.username = generate_username(user.primer_nombre, user.primer_apellido)
        user.email = generate_email(user.primer_nombre, user.primer_apellido)
        raw_password = generate_password(user.primer_nombre, user.primer_apellido, user.rut)
        user.set_password(raw_password)

        # NO reasignamos user.rol aquí; viene desde el formulario
        user.save()

        messages.success(
            self.request,
            f"Usuario creado: {user.username} | Email: {user.email} | Contraseña inicial: {raw_password} | Rol: {user.rol.nombre}"
        )
        return super().form_valid(form)

    
# EDITAR
class UserUpdateView(UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "core/usuarios/user_form.html"
    success_url = reverse_lazy("user_list")

# ELIMINAR
class UserDeleteView(DeleteView):
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
class DepartamentoListView(SoloRRHHMixin, ListView):
    model = Departamento
    template_name = "core/departamentos/departamento_list.html"
    context_object_name = "departamentos"
    paginate_by = 15
    ordering = ['nombre']
    
    def get_queryset(self):
        qs = super().get_queryset().annotate(total_tareas=Count('tasks'))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        return qs

class DepartamentoCreateView(SoloRRHHMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = "core/departamentos/departamento_form.html"
    success_url = reverse_lazy("departamento_list")

    def form_valid(self, form):
        messages.success(self.request, "Departamento creado correctamente.")
        return super().form_valid(form)

class DepartamentoUpdateView(SoloRRHHMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = "core/departamentos/departamento_form.html"
    success_url = reverse_lazy("departamento_list")

    def form_valid(self, form):
        messages.success(self.request, "Departamento actualizado correctamente.")
        return super().form_valid(form)

class DepartamentoDeleteView(SoloRRHHMixin, DeleteView):
    model = Departamento
    template_name = "core/departamentos/departamento_confirm_delete.html"
    success_url = reverse_lazy("departamento_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Bloquear borrado si hay tareas asociadas
        if Tarea.objects.filter(departamento=self.object).exists():
            messages.error(request, "No puedes eliminar este departamento porque tiene tareas asociadas.")
            return redirect("departamento_list")  # opcional: redirigir con HttpResponseRedirect
        messages.success(request, "Departamento eliminado correctamente.")
        return super().post(request, *args, **kwargs)



#CRUD TAREAS:
# LISTAR (Gerente/Supervisor)
class TareaListGSView(SoloGerenteSupervisorMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_gs.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ['fecha_limite', 'estado']

    def get_queryset(self):
        qs = super().get_queryset().select_related('departamento','asignado')
        q = self.request.GET.get("q","").strip()
        estado = self.request.GET.get("estado","").strip()
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
        return qs

# LISTAR (Trabajador)
class TareaListTrabajadorView(SoloTrabajadorMixin, ListView):
    model = Tarea
    template_name = "core/tareas/tarea_list_trab.html"
    context_object_name = "tareas"
    paginate_by = 20
    ordering = ['estado','fecha_limite']

    def get_queryset(self):
        return Tarea.objects.filter(asignado=self.request.user).select_related('departamento')
    
# CREAR
class TareaCreateView(SoloGerenteSupervisorMixin, CreateView):
    model = Tarea
    form_class = TareaForm
    template_name = "core/tareas/tarea_form.html"
    success_url = reverse_lazy("tarea_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        resp = super().form_valid(form)

        # 🔹 AUDIT: creada
        HistorialTarea.objects.create(
            tarea=self.object,
            accion="CREADA",
            realizado_por=self.request.user
        )

        # Notificación al asignado
        Notificacion.objects.create(
            usuario=self.object.asignado,
            mensaje=f"Se te asignó la tarea: {self.object.titulo}"
        )
        messages.success(self.request, "Tarea creada y asignada correctamente.")
        return resp

# EDITAR
class TareaUpdateView(SoloGerenteSupervisorMixin, UpdateView):
    model = Tarea
    form_class = TareaForm
    template_name = "core/tareas/tarea_form.html"
    success_url = reverse_lazy("tarea_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs
    
    def form_valid(self, form):
        original = Tarea.objects.get(pk=self.object.pk)  # 🔹 AUDIT: copia antes de guardar

        # Mantener tu regla de no tocar 'estado'
        u = self.request.user
        if getattr(u, "rol", None) and u.rol.nombre in ['Gerente','Supervisor']:
            form.instance.estado = self.get_object().estado

        resp = super().form_valid(form)

        # 🔹 AUDIT: compara y registra cambios (sin incluir 'estado' aquí)
        registrar_cambios_tarea(
            tarea=self.object,
            original=original,
            user=self.request.user,
            campos=['titulo', 'descripcion', 'departamento', 'asignado', 'fecha_limite']
        )
        return resp

# ELIMINAR
class TareaDeleteView(SoloGerenteSupervisorMixin, DeleteView):
    model = Tarea
    template_name = "core/tareas/tarea_confirm_delete.html"
    success_url = reverse_lazy("tarea_list_gs")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.estado == "Finalizada":
            messages.error(request, "No puedes eliminar una tarea ya finalizada.")
            return redirect("tarea_list_gs")

        # 🔹 AUDIT: marcar eliminada (antes de borrar)
        HistorialTarea.objects.create(
            tarea=obj,
            accion="ELIMINADA",
            valor_anterior=f"{obj.titulo}",
            realizado_por=request.user
        )
        return super().post(request, *args, **kwargs)

# DETALLE (todos los roles pueden ver si está asignado o con permisos)
class TareaDetailView(DetailView):
    model = Tarea
    template_name = "core/tareas/tarea_detail.html"
    context_object_name = "tarea"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        u = request.user
        # acceso: asignado, Gerente o Supervisor
        if not (u.is_authenticated and (u == obj.asignado or (u.rol and u.rol.nombre in ['Gerente','Supervisor']))):
            messages.error(request, "No tienes permiso para ver esta tarea.")
            return redirect("indexprueba")
        return super().dispatch(request, *args, **kwargs)
    
# CAMBIO DE ESTADO (Trabajador)
class TareaEstadoUpdateView(SoloTrabajadorMixin, UpdateView):
    model = Tarea
    form_class = TareaEstadoForm
    template_name = "core/tareas/tarea_estado_form.html"
    success_url = reverse_lazy("tarea_list_trab")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Solo el TRABAJADOR asignado puede cambiar estado
        if obj.asignado != request.user:
            messages.error(request, "Solo el asignado puede cambiar el estado.")
            return redirect("tarea_list_trab")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        tarea = self.get_object()
        estado_anterior = tarea.estado  # 🔹 AUDIT: capturar antes

        # Guardar pasando el usuario actual (tu lógica)
        self.object = form.save(user=self.request.user)

        # 🔹 AUDIT: registrar cambio de estado si hubo
        if estado_anterior != self.object.estado:
            HistorialTarea.objects.create(
                tarea=self.object,
                accion="ESTADO",
                campo="estado",
                valor_anterior=estado_anterior,
                valor_nuevo=self.object.estado,
                realizado_por=self.request.user
            )

        # 🔹 AUDIT: si se envió comentario opcional, lo registramos
        texto = (form.cleaned_data.get("comentario") or "").strip()
        if texto:
            HistorialTarea.objects.create(
                tarea=self.object,
                accion="COMENTARIO",
                campo="comentario",
                valor_nuevo=texto[:2000],
                realizado_por=self.request.user
            )

        messages.success(self.request, "Estado actualizado.")
        return redirect(self.get_success_url())


# EVALUACIONES:
# Listado global (Gerente ve todas; Supervisor también puede usar este con filtros si quieres)
class EvalListGSView(SoloGerenteSupervisorMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_gs.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset().select_related('trabajador','supervisor')
        q = self.request.GET.get("q","").strip()
        if q:
            qs = qs.filter(
                Q(trabajador__primer_nombre__icontains=q) |
                Q(trabajador__primer_apellido__icontains=q) |
                Q(supervisor__primer_nombre__icontains=q) |
                Q(supervisor__primer_apellido__icontains=q)
            )
        # Si es Supervisor (no gerente), por defecto ver solo las que él creó (a menos que quieras mostrar todas)
        u = self.request.user
        if u.rol and u.rol.nombre == 'Supervisor' and not u.is_superuser:
            qs = qs.filter(supervisor=u)
        return qs

# Listado para Trabajador: solo las mías
class EvalListTrabajadorView(SoloTrabajadorMixin, ListView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_list_trab.html"
    context_object_name = "evaluaciones"
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        return Evaluacion.objects.filter(trabajador=self.request.user).select_related('supervisor')

# Crear evaluación (solo Supervisor)
class EvalCreateView(SoloSupervisorMixin, CreateView):
    model = Evaluacion
    form_class = EvaluacionForm
    template_name = "core/evaluaciones/eval_form.html"
    success_url = reverse_lazy("eval_list_gs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.supervisor = self.request.user
        response = super().form_valid(form)

        # 🔹 AUDIT
        HistorialEvaluacion.objects.create(
            evaluacion=self.object,
            accion="CREADA",
            realizado_por=self.request.user
        )

        Notificacion.objects.create(
            usuario=self.object.trabajador,
            mensaje=f"Has recibido una evaluación (puntaje {self.object.puntaje})."
        )
        messages.success(self.request, "Evaluación registrada correctamente.")
        return response

# Editar evaluación (solo quien la creó o Gerente)
class EvalUpdateView(SoloGerenteSupervisorMixin, UpdateView):
    model = Evaluacion
    form_class = EvaluacionForm
    template_name = "core/evaluaciones/eval_form.html"
    success_url = reverse_lazy("eval_list_gs")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        u = request.user
        if u.rol and u.rol.nombre == 'Supervisor' and obj.supervisor != u and not u.is_superuser:
            messages.error(request, "Solo puedes editar evaluaciones creadas por ti.")
            return redirect("eval_list_gs")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs
    
    def form_valid(self, form):
        original = Evaluacion.objects.get(pk=self.object.pk)  # 🔹 AUDIT: copia antes
        self.object = form.save()

        # 🔹 AUDIT: qué campos auditar
        registrar_cambios_eval(
            evaluacion=self.object,
            original=original,
            user=self.request.user,
            campos=['puntaje', 'comentarios', 'trabajador']  # quita 'trabajador' si no quieres auditar reasignación
        )

        Notificacion.objects.create(
            usuario=self.object.trabajador,
            mensaje=f"Tu evaluación fue actualizada (puntaje {self.object.puntaje})."
        )
        messages.success(self.request, "Evaluación actualizada.")
        return redirect(self.get_success_url())

# Eliminar evaluación (autor o Gerente)
class EvalDeleteView(SoloGerenteSupervisorMixin, DeleteView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_confirm_delete.html"
    success_url = reverse_lazy("eval_list_gs")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        u = request.user
        if u.rol and u.rol.nombre == 'Supervisor' and obj.supervisor != u and not u.is_superuser:
            messages.error(request, "Solo puedes eliminar evaluaciones creadas por ti.")
            return redirect("eval_list_gs")

        # 🔹 AUDIT
        HistorialEvaluacion.objects.create(
            evaluacion=obj,
            accion="ELIMINADA",
            valor_anterior=f"Puntaje {obj.puntaje}; Comentarios: {obj.comentarios or ''}",
            realizado_por=request.user
        )

        messages.success(request, "Evaluación eliminada.")
        return super().post(request, *args, **kwargs)

# DASHBOARD/REPORTES:
class DashboardView(SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Usuarios por rol
        usuarios_por_rol = (User.objects
                            .values("rol__nombre")
                            .annotate(total=Count("id"))
                            .order_by("rol__nombre"))

        # Tareas por estado
        tareas_por_estado = (Tarea.objects
                             .values("estado")
                             .annotate(total=Count("id"))
                             .order_by("estado"))

        # Tareas atrasadas
        atrasadas = Tarea.objects.filter(estado__in=["Pendiente","En progreso"], fecha_limite__lt=now().date()).count()

        # Tareas por departamento
        tareas_por_depto = (Tarea.objects
                            .values("departamento__nombre")
                            .annotate(total=Count("id"))
                            .order_by("departamento__nombre"))

        # Promedio de evaluaciones por trabajador (top 10)
        top_trabajadores = (Evaluacion.objects
                            .values("trabajador__id","trabajador__primer_nombre","trabajador__primer_apellido")
                            .annotate(prom=Avg("puntaje"), total=Count("id"))
                            .order_by("-prom")[:10])

        # Promedio por departamento (si trabajador tiene FK a depto en tu modelo; si no, omítelo)
        # Suponiendo que Tarea vincula depto y queremos promedio por depto del asignado (aprox.)
        # Si no aplica a tu modelo, comenta este bloque.
        # prom_por_depto = (EvaluacionDesempeno.objects
        #                   .values("trabajador__departamento__nombre")
        #                   .annotate(prom=Avg("puntaje"))
        #                   .order_by("-prom"))

        ctx.update({
            "usuarios_por_rol": usuarios_por_rol,
            "tareas_por_estado": tareas_por_estado,
            "tareas_atrasadas": atrasadas,
            "tareas_por_depto": tareas_por_depto,
            "top_trabajadores": top_trabajadores,
            # "prom_por_depto": prom_por_depto,
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
    qs = Tarea.objects.select_related("departamento","asignado")
    estado = request.GET.get("estado","").strip()
    depto = request.GET.get("depto","").strip()
    asignado = request.GET.get("asignado","").strip()
    f_ini = parse_fecha(request.GET.get("f_ini",""))
    f_fin = parse_fecha(request.GET.get("f_fin",""))

    if estado:
        qs = qs.filter(estado=estado)
    if depto:
        qs = qs.filter(departamento_id=depto)
    if asignado:
        qs = qs.filter(asignado_id=asignado)
    if f_ini:
        qs = qs.filter(fecha_limite__gte=f_ini)
    if f_fin:
        qs = qs.filter(fecha_limite__lte=f_fin)
    return qs

def filtrar_evaluaciones(request):
    qs = Evaluacion.objects.select_related("trabajador","supervisor")
    trabajador = request.GET.get("trabajador","").strip()
    supervisor = request.GET.get("supervisor","").strip()
    f_ini = parse_fecha(request.GET.get("f_ini",""))
    f_fin = parse_fecha(request.GET.get("f_fin",""))
    puntaje = request.GET.get("puntaje","").strip()

    if trabajador:
        qs = qs.filter(trabajador_id=trabajador)
    if supervisor:
        qs = qs.filter(supervisor_id=supervisor)
    if f_ini:
        qs = qs.filter(created_at__date__gte=f_ini)
    if f_fin:
        qs = qs.filter(created_at__date__lte=f_fin)
    if puntaje:
        qs = qs.filter(puntaje=puntaje)
    return qs

# -----------------------
# REPORTES TAREAS (lista + filtros)
# -----------------------
class ReporteTareasView(SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/reportes/reporte_tareas.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = filtrar_tareas(self.request).order_by("fecha_limite","estado")
        ctx["tareas"] = qs
        ctx["departamentos"] = Departamento.objects.all().order_by("nombre")
        ctx["trabajadores"] = User.objects.filter(rol__nombre="Trabajador").order_by("primer_apellido","primer_nombre")
        return ctx

def exportar_tareas_csv(request):
    qs = filtrar_tareas(request).order_by("fecha_limite","estado")
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

def exportar_tareas_xlsx(request):
    qs = filtrar_tareas(request).order_by("fecha_limite","estado")
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
def exportar_tareas_pdf(request):
    qs = filtrar_tareas(request).order_by("fecha_limite","estado")
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
class ReporteEvaluacionesView(SoloGerenteSupervisorMixin, TemplateView):
    template_name = "core/reportes/reporte_evaluaciones.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = filtrar_evaluaciones(self.request).order_by("-created_at")
        # Resumen: promedio por trabajador (con filtros aplicados)
        resumen = (qs.values("trabajador__id","trabajador__primer_nombre","trabajador__primer_apellido")
                     .annotate(prom=Avg("puntaje"), total=Count("id"))
                     .order_by("-prom"))
        ctx["evaluaciones"] = qs
        ctx["resumen_trabajadores"] = resumen
        ctx["trabajadores"] = User.objects.filter(rol__nombre="Trabajador").order_by("primer_apellido","primer_nombre")
        ctx["supervisores"] = User.objects.filter(rol__nombre="Supervisor").order_by("primer_apellido","primer_nombre")
        return ctx

def exportar_evals_csv(request):
    qs = filtrar_evaluaciones(request).order_by("-created_at")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reporte_evaluaciones.csv"'
    writer = csv.writer(response)
    writer.writerow(["Trabajador","Supervisor","Puntaje","Fecha","Comentarios"])
    for e in qs:
        writer.writerow([
            f"{e.trabajador.primer_nombre} {e.trabajador.primer_apellido}",
            f"{e.supervisor.primer_nombre} {e.supervisor.primer_apellido}",
            e.puntaje,
            e.created_at.strftime("%Y-%m-%d %H:%M"),
            (e.comentarios or "").replace("\n"," ").strip()
        ])
    return response

def exportar_evals_xlsx(request):
    qs = filtrar_evaluaciones(request).order_by("-created_at")
    if openpyxl is None:
        return HttpResponse("openpyxl no está instalado. Instala con: pip install openpyxl", status=500)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Evaluaciones"
    ws.append(["Trabajador","Supervisor","Puntaje","Fecha","Comentarios"])
    for e in qs:
        ws.append([
            f"{e.trabajador.primer_nombre} {e.trabajador.primer_apellido}",
            f"{e.supervisor.primer_nombre} {e.supervisor.primer_apellido}",
            e.puntaje,
            e.created_at.strftime("%Y-%m-%d %H:%M"),
            (e.comentarios or "").strip()
        ])
    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = 'attachment; filename="reporte_evaluaciones.xlsx"'
    return resp

# Exportar EVALUACIONES a PDF
def exportar_evals_pdf(request):
    qs = filtrar_evaluaciones(request).order_by("-created_at")
    context = {
        "evaluaciones": qs,
        "filtros": request.GET,
        "titulo": "Tareas",
        "now": now(),
    }
    return render_to_pdf("core/reportes/pdf_evaluaciones.html", context, filename="reporte_evaluaciones.pdf")

def pdfbase(request):
    return render(request, 'core/reportes/pdf_base.html')

# HISTORIAL DE CAMBIOS (solo Gerente/Supervisor):
class TareaHistorialView(SoloGerenteSupervisorMixin, DetailView):
    model = Tarea
    template_name = "core/tareas/tarea_historial.html"
    context_object_name = "tarea"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = self.object.historial.select_related("realizado_por")
        return ctx

class EvalHistorialView(SoloGerenteSupervisorMixin, DetailView):
    model = Evaluacion
    template_name = "core/evaluaciones/eval_historial.html"
    context_object_name = "evaluacion"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = self.object.historial.select_related("realizado_por")
        return ctx





































'''
creo que esto es necesario para la app móvil
# Iniciar y cerrar sesión )
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Sesión cerrada correctamente'}, status=status.HTTP_200_OK)
'''