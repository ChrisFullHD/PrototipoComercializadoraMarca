from django.db import models
from inventario.models import Producto, Instancia_Producto_Unitario
# Create your models here.

class Devolucion(models.Model):
    producto = models.ForeignKey(Instancia_Producto_Unitario, on_delete=models.CASCADE)
    motivo = models.CharField(max_length=200)
    fecha = models.DateField(auto_now_add=True)
    

class Baja(models.Model):
    producto = models.ForeignKey(Instancia_Producto_Unitario, on_delete=models.CASCADE)
    motivo = models.CharField(max_length=200)
    fecha = models.DateField(auto_now_add=True)
    