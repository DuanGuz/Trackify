from django.contrib import admin
from .models import *

class RolAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at', 'updated_at']
    search_fields = ['nombre']
    list_per_page = 10
    list_filter = ['nombre']
    list_editable = ['nombre', 'descripcion']

class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'rol', 'is_active', 'calificacion_promedio', 'created_at', 'updated_at']
    search_fields = ['username', 'email', 'rol__nombre']
    list_per_page = 10
    list_filter = ['rol', 'is_active']
    list_editable = ['email', 'rol', 'is_active', 'calificacion_promedio']

class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at', 'updated_at']
    search_fields = ['nombre']
    list_per_page = 10
    list_filter = ['nombre']
    list_editable = ['nombre', 'descripcion']

class ProyectoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'department', 'supervisor', 'created_at', 'updated_at']
    search_fields = ['nombre', 'department__nombre', 'supervisor__username']
    list_per_page = 10
    list_filter = ['department', 'supervisor']
    list_editable = ['nombre', 'descripcion', 'department', 'supervisor']

class TareaAdmin(admin.ModelAdmin):
    list_display = ['id', 'titulo', 'descripcion', 'estado', 'asignado', 'proyecto', 'fecha_limite', 'created_at', 'updated_at']
    search_fields = ['titulo', 'estado', 'asignado__username', 'proyecto__nombre']
    list_per_page = 10
    list_filter = ['estado', 'asignado', 'proyecto']
    list_editable = ['titulo', 'descripcion', 'estado', 'asignado', 'proyecto', 'fecha_limite']

class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ['id', 'worker', 'supervisor', 'score', 'comments', 'created_at']
    search_fields = ['worker__username', 'supervisor__username']
    list_per_page = 10
    list_filter = ['score', 'supervisor', 'worker']
    list_editable = ['score', 'comments']

class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'mensaje', 'is_read', 'created_at']
    search_fields = ['usuario__username', 'mensaje']
    list_per_page = 10
    list_filter = ['is_read', 'usuario']
    list_editable = ['mensaje', 'is_read']

class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'filtro', 'generado', 'created_at']
    search_fields = ['nombre', 'generado__username']
    list_per_page = 10
    list_filter = ['generado']
    list_editable = ['nombre', 'filtro']

class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['id', 'tarea', 'usuario', 'contenido', 'created_at']
    search_fields = ['tarea__titulo', 'usuario__username', 'contenido']
    list_per_page = 10
    list_filter = ['usuario', 'tarea']
    list_editable = ['tarea', 'usuario', 'contenido']

# Registrar los modelos en el panel de administración
admin.site.register(Rol, RolAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Departamento, DepartamentoAdmin)
admin.site.register(Proyecto, ProyectoAdmin)
admin.site.register(Tarea, TareaAdmin)
admin.site.register(PerformanceEvaluation, PerformanceEvaluationAdmin)
admin.site.register(Notificacion, NotificacionAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Comentario, ComentarioAdmin)