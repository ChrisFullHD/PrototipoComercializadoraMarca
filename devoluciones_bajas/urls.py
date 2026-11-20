from django.urls import path 
from . import views 
urlpatterns = [ 
    #devoluciones
    path('devoluciones/', views.lista_devoluciones, name='lista_devoluciones'),
    path('devoluciones/crear/', views.crear_devolucion, name='crear_devolucion'),
    path('devoluciones/<int:pk>/', views.detalle_devolucion, name='detalle_devolucion'),
    path('devoluciones/<int:pk>/eliminar/', views.eliminar_devolucion, name='eliminar_devolucion'),
    #bajas
    path('bajas/', views.lista_bajas, name='lista_bajas'),
    path('bajas/crear/', views.crear_baja, name='crear_baja'),
    path('bajas/<int:pk>/', views.detalle_baja, name='detalle_baja'),
    path('bajas/<int:pk>/eliminar/', views.eliminar_baja, name='eliminar_baja'),
   
] 