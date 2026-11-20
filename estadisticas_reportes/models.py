from django.db import models
from usuarios.models import Perfil

# Create your models here.
class Reporte(models.Model):
    reporte = models.FileField(upload_to='reportes/')
    fecha = models.DateField(auto_now_add=True)
    usuario = models.ForeignKey(Perfil,on_delete=models.PROTECT)
    
    def __str__(self):
        return f'{self.fecha}'