from django.db import models
from inventario.models import Producto, Instancia_Producto_Unitario
# Create your models here.

class Devolucion(models.Model):
    motivo = models.CharField(max_length=200)
    fecha = models.DateField(auto_now_add=True)
    producto = models.ForeignKey(Instancia_Producto_Unitario, on_delete=models.CASCADE)

class Baja(models.Model):
    motivo = models.CharField(max_length=200)
    fecha = models.DateField(auto_now_add=True)
    producto = models.ForeignKey(Instancia_Producto_Unitario, on_delete=models.CASCADE)