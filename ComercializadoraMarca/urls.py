from django.contrib import admin 
from django.urls import path, include 
from django.conf import settings 
from django.conf.urls.static import static 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('inventario/', include('inventario.urls')),
    path('facturas/', include('facturas.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('estadisticas_reportes/', include('estadisticas_reportes.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('ventas/', include('ventas.urls')),
    path('devoluciones_bajas/', include('devoluciones_bajas.urls')),
    path('proveedores/', include('proveedores.urls')),
]

if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 