from django.contrib import admin
from .models import Venta, Detalle_Venta, VentaFiada

# Register your models here.
admin.site.register(Venta)
admin.site.register(Detalle_Venta)
admin.site.register(VentaFiada)