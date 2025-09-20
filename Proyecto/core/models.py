from django.db import models
from django.contrib.auth.models import AbstractUser

# Modelo de Rol
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)  
    descripcion = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

# Modelo de Usuario
class User(AbstractUser):
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, related_name='users') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

# Modelo de Departamento
class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

# Modelo de Tarea
class Tarea(models.Model):
    ESTADO = [
        ('Pendiente', 'Pendiente'),
        ('En progreso', 'En progreso'),
        ('Atrasada', 'Atrasada'),
        ('Finalizada', 'Finalizada'),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO, default='Pendiente')
    asignado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='tasks')
    fecha_limite = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo

# Modelo de Evaluación (Calificación de desempeño)
class Evaluacion(models.Model):
    trabajador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluaciones', limit_choices_to={'rol__nombre': 'Trabajador'})
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluaciones_dadas', limit_choices_to={'rol__nombre': 'Supervisor'})
    puntaje = models.IntegerField()
    comentarios = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluación de {self.trabajador.username} por {self.supervisor.username}"

# Modelo de Notificación
class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    mensaje = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación para {self.usuario.username}"

# Modelo de Comentario
class Comentario(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='comments')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    contenido = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.usuario.username} en {self.tarea.titulo}"

# Modelo de Turno
class Turno(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turnos')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Turno de {self.usuario.username} - {self.fecha}"
