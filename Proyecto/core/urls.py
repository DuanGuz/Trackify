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

    # EVALUACIONES:
    path("evaluaciones/", EvalListGSView.as_view(), name="eval_list_gs"), # Gerente/Supervisor
    path("mis-evaluaciones/", EvalListTrabajadorView.as_view(), name="eval_list_trab"), # Trabajador
    path("evaluaciones/nueva/", EvalCreateView.as_view(), name="eval_create"), # Supervisor
    path("evaluaciones/<int:pk>/editar/", EvalUpdateView.as_view(), name="eval_update"),
    path("evaluaciones/<int:pk>/eliminar/", EvalDeleteView.as_view(), name="eval_delete"),

    #DASHBOARD/REPORTES:
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reportes/tareas/", ReporteTareasView.as_view(), name="reporte_tareas"),
    path("reportes/tareas/pdf/", exportar_tareas_pdf, name="reporte_tareas_pdf"),
    path("reportes/tareas/xlsx/", exportar_tareas_xlsx, name="reporte_tareas_xlsx"),

    path("reportes/evaluaciones/", ReporteEvaluacionesView.as_view(), name="reporte_evaluaciones"),
    path("reportes/evaluaciones/pdf/", exportar_evals_pdf, name="reporte_evals_pdf"),
    path("reportes/evaluaciones/xlsx/", exportar_evals_xlsx, name="reporte_evals_xlsx"),
    path("reportes/pdf-base", pdfbase, name="reporte_pdf_base"),

    #HISTORIAL DE TAREAS Y EVALUACIONES:
    path("tareas/<int:pk>/historial/", TareaHistorialView.as_view(), name="tarea_historial"),
    path("evaluaciones/<int:pk>/historial/", EvalHistorialView.as_view(), name="eval_historial"),

    #PERFIL Y CAMBIO DE PASSWORD:
    path("perfil/", PerfilView.as_view(), name="perfil"),
    path("perfil/editar/", PerfilUpdateView.as_view(), name="perfil_editar"),
    path("perfil/password/", MiPasswordChangeView.as_view(), name="perfil_password"),

    #sms:
    path("password/sms/", password_reset_sms_request, name="password_reset_sms_request"),
    path("password/sms/verificar/", password_reset_sms_verify, name="password_reset_sms_verify"),
]