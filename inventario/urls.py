from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_productos, name="lista_productos"),
    path("producto/buscar-codigo/", views.buscar_producto_codigo, name="buscar_producto_codigo"),
    path("producto/nuevo/", views.crear_producto, name="producto_crear"),
    path("producto/<int:pk>/editar/", views.editar_producto, name="producto_editar"),
    path(
        "producto/<int:pk>/eliminar/",
        views.eliminar_producto,
        name="producto_eliminar",
    ),
    path(
        "instancia-unitaria/nueva/",
        views.crear_instancia_unitaria,
        name="instancia_unitaria_crear",
    ),
    path(
        "instancia-unitaria/<int:pk>/editar/",
        views.editar_instancia_unitaria,
        name="instancia_unitaria_editar",
    ),
    path(
        "instancia-unitaria/<int:pk>/eliminar/",
        views.eliminar_instancia_unitaria,
        name="instancia_unitaria_eliminar",
    ),
    path(
        "instancia-peso/nueva/",
        views.crear_instancia_peso,
        name="instancia_peso_crear",
    ),
    path(
        "instancia-peso/<int:pk>/editar/",
        views.editar_instancia_peso,
        name="instancia_peso_editar",
    ),
    path(
        "instancia-peso/<int:pk>/eliminar/",
        views.eliminar_instancia_peso,
        name="instancia_peso_eliminar",
    ),
    path("categorias/", views.lista_categorias, name="lista_categorias"),
    path("categorias/nueva/", views.crear_categoria, name="categoria_crear"),
    path(
        "categorias/<int:pk>/editar/",
        views.editar_categoria,
        name="categoria_editar",
    ),
    path(
        "categorias/<int:pk>/eliminar/",
        views.eliminar_categoria,
        name="categoria_eliminar",
    ),
    path("lotes/", views.lista_lotes, name="lista_lotes"),
    path("lotes/nuevo/", views.crear_lote, name="lote_crear"),
    path("lotes/<int:pk>/editar/", views.editar_lote, name="lote_editar"),
    path("lotes/<int:pk>/eliminar/", views.eliminar_lote, name="lote_eliminar"),
]
