from django.urls import path
from . import views

urlpatterns = [
    # Ventas
    path('', views.lista_ventas, name='lista_ventas'),
    path('registrar/', views.registrar_venta, name='registrar_venta'),
    path('<int:pk>/', views.detalle_venta, name='detalle_venta'),
    path('<int:pk>/eliminar/', views.eliminar_venta, name='eliminar_venta'),

    # Ventas fiadas
    path('fiadas/', views.lista_ventas_fiadas, name='lista_ventas_fiadas'),
    path('fiadas/<int:pk>/', views.detalle_venta_fiada, name='detalle_venta_fiada'),
    path('fiadas/<int:pk>/editar/', views.editar_venta_fiada, name='editar_venta_fiada'),
    path('fiadas/<int:pk>/eliminar/', views.eliminar_venta_fiada, name='eliminar_venta_fiada'),
]