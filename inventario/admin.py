from django.contrib import admin
from .models import Producto_Unitario, Instancia_Producto_Peso, Instancia_Producto_Unitario, Lote, Categoria

admin.site.register(Categoria)
admin.site.register(Lote)
admin.site.register(Producto_Unitario)
admin.site.register(Instancia_Producto_Unitario)
admin.site.register(Instancia_Producto_Peso)
