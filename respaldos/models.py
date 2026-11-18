from django.db import models
from usuarios.models import Perfil

# Create your models here.
class Respaldos(models.Model):
    nombre = models.CharField(max_length=100)
    respaldo = models.FileField(upload_to='respaldos/')
    fecha = models.DateField(auto_now_add=True)
    usuario = models.ForeignKey(Perfil, on_delete=models.PROTECT)
    
    def __str__(self):
        return f'{self.fecha} - {self.nombre}'