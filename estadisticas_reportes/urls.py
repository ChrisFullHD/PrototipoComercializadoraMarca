from django.urls import path 
from . import views 
urlpatterns = [ 
    path('', views.panel_estadisticas, name='panel_estadisticas'),
    path('ventas/', views.ventas_totales, name='ventas_totales'),
    path('rotacion/', views.productos_mayor_rotacion, name='productos_mayor_rotacion'),
    path('stock/', views.stock_productos, name='stock_productos'),
]