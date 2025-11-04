from django.urls import path
from .views import *
from .api_views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views_billing import *

urlpatterns = [
     path('', lambda request: redirect('index')),  # Redirige la raíz a /inicio/
    path('inicio/', index, name='index'),
    path('home/', home, name='home'),
    path('base/', base, name="base"),
    path('auth-confirm/', auth_confirm, name="auth_confirm"),

    #PRUEBA LOGIN WEB
    path('login/', web_login, name='web_login'), #LISTO
    path('logout/', web_logout, name='web_logout'),
    path('baseprueba/', baseprueba, name='baseprueba'),

    path('registro-web/', registro_web, name='registro_web'), 
    #path('registro/', registro_gerente, name='registro'),

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
    path("tareas/mias/", TareaListSupervisorMiasView.as_view(), name="tarea_list_supervisor_mias"),
    path("tareas/equipo/", TareaListSupervisorEquipoView.as_view(), name="tarea_list_supervisor_equipo"),

    # Trabajador
    path("mis-tareas/", TareaListTrabajadorView.as_view(), name="tarea_list_trab"),
    path("tareas/<int:pk>/estado/", TareaEstadoUpdateView.as_view(), name="tarea_estado"),

    # Detalle (común)
    path("tareas/<int:pk>/", TareaDetailView.as_view(), name="tarea_detail"),

    # EVALUACIONES:
    path('evaluaciones/', EvalListGSView.as_view(), name='eval_list_gs'),
    path('evaluaciones/nueva/', EvalCreateView.as_view(), name='eval_create'),
    path('evaluaciones/<int:pk>/editar/', EvalGeneralUpdateView.as_view(), name='eval_update'),
    path('evaluaciones/<int:pk>/eliminar/', EvalGeneralDeleteView.as_view(), name='eval_delete'),
    path('mis-evaluaciones/', EvalMisEvaluacionesView.as_view(), name='eval_list_mias'),

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
    path("password-reset/sms/", password_reset_sms_request, name="password_reset_sms_request"),
    path("password-reset/sms/verify/", password_reset_sms_verify_code, name="password_reset_sms_verify"),
    path("password-reset/sms/change/", password_reset_sms_change, name="password_reset_sms_change"),

    # Auth JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Endpoints Trabajador
    path("api/tareas/mias/", MisTareasAPI.as_view(), name="api_mis_tareas"),
    path("api/tareas/<int:pk>/estado/", TareaEstadoAPI.as_view(), name="api_tarea_estado"),
    path("api/evaluaciones/mias/", MisEvaluacionesAPI.as_view(), name="api_mis_evaluaciones"),
    path("api/me/", MeAPI.as_view(), name="api_me"),

    #Notifiaciones
    path("notificaciones/", notif_list_api, name="notif_list_api"),
    path("notificaciones/clear/", notif_clear_api, name="notif_clear_api"),
    path("notificaciones/delete_all/", notif_delete_all_api, name="notif_delete_all_api"),
    
    # Endpoints RRHH y Gerente/Supervisor
    path("api/usuarios-por-rol-depto/", api_usuarios_por_rol_y_depto, name="api_usuarios_por_rol_y_depto"),

    path("billing/", billing_overview, name="billing_overview"),
    path("billing/checkout/", billing_checkout, name="billing_checkout"),
    path("billing/success/", billing_success, name="billing_success"),
    path("billing/failure/", billing_failure, name="billing_failure"),
    path("billing/pending/", billing_pending, name="billing_pending"),
    path("billing/refresh/", billing_refresh, name="billing_refresh"),

    # Webhooks
    path("webhooks/mercadopago/", mercadopago_webhook, name="mercadopago_webhook"),
]