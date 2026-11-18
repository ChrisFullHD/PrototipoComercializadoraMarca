from django.db import models

# Create your models here.
class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, verbose_name='Nombre', unique=True)
    descripcion = models.TextField(verbose_name='Descripcion')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')

    def __str__(self):
        return self.nombre