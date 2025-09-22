from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name="index"),
    path('base/', base, name="base"),
    path('auth-confirm/', auth_confirm, name="auth_confirm"),
    path('profile/', profile, name="profile"),

    #PRUEBA LOGIN WEB
    path('login/', web_login, name='web_login'),
    path('logout/', web_logout, name='web_logout'),
    path('indexprueba/', indexprueba, name='indexprueba'),
    path('baseprueba/', baseprueba, name='baseprueba'),
    path('registro/', registro_gerente, name='registro'),

    #CRUD USUARIOS(RRHH):
    path("usuarios/", UserListView.as_view(), name="user_list"),
    path("usuarios/nuevo/", RRHHUserCreateView.as_view(), name="user_create"),
    path("usuarios/<int:pk>/editar/", UserUpdateView.as_view(), name="user_update"),
    path("usuarios/<int:pk>/eliminar/", UserDeleteView.as_view(), name="user_delete"),

    #CRUD DEPARTAMENTOS (RRHH):
    path("departamentos/", DepartamentoListView.as_view(), name="departamento_list"),
    path("departamentos/nuevo/", DepartamentoCreateView.as_view(), name="departamento_create"),
    path("departamentos/<int:pk>/editar/", DepartamentoUpdateView.as_view(), name="departamento_update"),
    path("departamentos/<int:pk>/eliminar/", DepartamentoDeleteView.as_view(), name="departamento_delete"),

    # Gerente/Supervisor
    path("tareas/", TareaListGSView.as_view(), name="tarea_list_gs"),
    path("tareas/nueva/", TareaCreateView.as_view(), name="tarea_create"),
    path("tareas/<int:pk>/editar/", TareaUpdateView.as_view(), name="tarea_update"),
    path("tareas/<int:pk>/eliminar/", TareaDeleteView.as_view(), name="tarea_delete"),

    # Trabajador
    path("mis-tareas/", TareaListTrabajadorView.as_view(), name="tarea_list_trab"),
    path("tareas/<int:pk>/estado/", TareaEstadoUpdateView.as_view(), name="tarea_estado"),

    # Detalle (común)
    path("tareas/<int:pk>/", TareaDetailView.as_view(), name="tarea_detail"),
]