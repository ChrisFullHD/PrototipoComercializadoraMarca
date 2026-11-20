from django.urls import path 
from . import views 
urlpatterns = [ 
    #proveedores
    path('', views.lista_proveedores, name='lista_proveedores'),
    path('crear/', views.crear_proveedores, name='crear_proveedores'),
    path('<int:pk>/', views.detalle_proveedores, name='detalle_proveedores'),
    path('<int:pk>/editar/', views.editar_proveedores, name='editar_proveedores'),
    path('<int:pk>/eliminar/', views.eliminar_proveedores, name='eliminar_proveedores'),
]