from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout, get_user_model
from .serializers import UserSerializer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import *
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.urls import reverse_lazy
from .models import *
from .utils import *
from django.db.models import Q, Count
from .mixins import *

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
        # Si el usuario es GS, asegúrate de NO cambiar estado aunque lo manden en el POST
        u = self.request.user
        if getattr(u, "rol", None) and u.rol.nombre in ['Gerente','Supervisor']:
            # reemplaza estado con el valor actual de la instancia
            form.instance.estado = self.get_object().estado
        return super().form_valid(form)

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
        # Guardar pasando el usuario actual
        self.object = form.save(user=self.request.user)
        messages.success(self.request, "Estado actualizado.")
        # Importante: redirigir manualmente, NO llamar a super().form_valid()
        return redirect(self.get_success_url())

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