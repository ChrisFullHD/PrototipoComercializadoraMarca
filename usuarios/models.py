from django.db import models
from django.contrib.auth.models import User

def rol_usuario_default():
    rol, _ = Rol.objects.get_or_create(nombre='Empleado')
    return rol.id

# Roles sistema: Administrador - Empleado (default)
class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Perfil(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.RESTRICT, default=rol_usuario_default)
    # El campo user cada usuario tiene un solo perfil
    # Cada perfil pertenece a un solo usuario
    user = models.OneToOneField(User, on_delete=models.CASCADE) # Si se elimina el usuario, también se elimina su perfil

    def __str__(self):
        return f"{self.user.username} - {self.rol.nombre}"