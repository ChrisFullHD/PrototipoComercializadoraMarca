from django.db import models

# Create your models here.
class Proveedor(models.Model):
    
    TIPO_CONTRIBUYENTE =[
        ('EMP', 'Empresa'),
        ('PER', 'Persona Natural'),
    ]

    TIPO_CUENTA = [
        ('CC', 'Cuenta Corriente'),
        ('CV', 'Cuenta Vista / Cuenta Rut'),
        ('CA', 'Cuenta de ahorro'),
        ('CE', 'Cuenta Electrónica'),
    ]
    nombre_fantasia = models.CharField(max_length=100, verbose_name='Nombre', unique=True, blank=True)  
    razon_social = models.CharField(max_length=100, verbose_name='Razón Social', unique=True)
    rut = models.CharField(max_length=12, verbose_name='RUT', unique=True)
    descripcion = models.TextField(verbose_name='Descripcion')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    giro_sii = models.CharField(max_length=100, verbose_name='Giro SII')
    direccion_tributaria = models.CharField(max_length=100, verbose_name='Dirección Tributaria')
    comuna = models.CharField(max_length=100, verbose_name='Comuna')
    email = models.EmailField(max_length=100, verbose_name='Email', unique=True)
    banco = models.CharField(max_length=100, verbose_name='Banco')
    numero_cuenta = models.CharField(max_length=20, verbose_name='Número de Cuenta')
    tipo_contribuyente = models.CharField(max_length=3, choices=TIPO_CONTRIBUYENTE, default='EMP')
    tipo_cuenta = models.CharField(max_length=2, choices=TIPO_CUENTA, default='CC')
    

    def __str__(self):
        return f'{self.razon_social} - {self.telefono}'