from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Sum
from django.db.models.deletion import RestrictedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.views import administrador_requerido

from .barcodes import barcode_lookup_values
from .forms import (
    CategoriaForm,
    Instancia_Producto_PesoForm,
    Instancia_Producto_UnitarioForm,
    LoteForm,
    Producto_UnitarioForm,
)
from .models import (
    Categoria,
    Instancia_Producto_Peso,
    Instancia_Producto_Unitario,
    Lote,
    Producto_Unitario,
)


def _render_form(
    request,
    form_class,
    page_title,
    cancel_url,
    instance=None,
    barcode_reader=False,
):
    form = form_class(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{page_title} correctamente.")
        return redirect(cancel_url)

    return render(
        request,
        "producto/form.html",
        {
            "form": form,
            "page_title": page_title,
            "cancel_url": cancel_url,
            "barcode_reader": barcode_reader,
        },
    )


def _confirm_delete(
    request,
    obj,
    cancel_url,
    success_message,
    error_message,
    deleted_instance_count=0,
):
    if request.method == "POST":
        try:
            obj.delete()
        except (ProtectedError, RestrictedError):
            messages.error(request, error_message)
        else:
            messages.success(request, success_message)
        return redirect(cancel_url)

    return render(
        request,
        "producto/confirm_delete.html",
        {
            "object": obj,
            "form": forms.Form(),
            "cancel_url": cancel_url,
            "deleted_instance_count": deleted_instance_count,
        },
    )


@login_required
def lista_productos(request):
    context = {
        "producto_unitario": Producto_Unitario.objects.select_related("categoria").all(),
        "instancias_producto_unitario": Instancia_Producto_Unitario.objects.select_related(
            "producto", "lote"
        ).all(),
        "instancias_producto_peso": Instancia_Producto_Peso.objects.select_related(
            "producto", "lote"
        ).all(),
    }
    return render(request, "producto/producto_list.html", context)


@login_required
def buscar_producto_codigo(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    codigo = request.GET.get("codigo", "").strip()
    try:
        lookup_values = barcode_lookup_values(codigo)
    except ValueError as error:
        return render(
            request,
            "producto/barcode_result.html",
            {"estado": "invalido", "mensaje": str(error), "codigo": codigo},
        )

    producto = (
        Producto_Unitario.objects.filter(codigo_barras__in=lookup_values)
        .select_related("categoria")
        .first()
    )
    if producto is None:
        return render(
            request,
            "producto/barcode_result.html",
            {
                "estado": "no_encontrado",
                "mensaje": "No hay un producto registrado con ese código.",
                "codigo": codigo,
            },
        )

    peso_stock = (
        producto.instancia_producto_peso.aggregate(total=Sum("cantidad_kg"))["total"]
        or 0
    )
    return render(
        request,
        "producto/barcode_result.html",
        {
            "estado": "encontrado",
            "mensaje": "Producto encontrado.",
            "codigo": codigo,
            "producto": producto,
            "peso_stock": peso_stock,
        },
    )


@login_required
@administrador_requerido
def crear_producto(request):
    return _render_form(
        request,
        Producto_UnitarioForm,
        "Agregar un Producto",
        "lista_productos",
        barcode_reader=True,
    )


@login_required
@administrador_requerido
def editar_producto(request, pk):
    producto = get_object_or_404(Producto_Unitario, pk=pk)
    return _render_form(
        request,
        Producto_UnitarioForm,
        "Modificar datos de un Producto",
        "lista_productos",
        instance=producto,
        barcode_reader=True,
    )


@login_required
@administrador_requerido
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto_Unitario, pk=pk)
    deleted_instance_count = (
        producto.instancia_producto_unitario.count()
        + producto.instancia_producto_peso.count()
    )
    return _confirm_delete(
        request,
        producto,
        "lista_productos",
        "Producto eliminado",
        "No se pudo eliminar el producto.",
        deleted_instance_count,
    )


@login_required
@administrador_requerido
def crear_instancia_unitaria(request):
    return _render_form(
        request,
        Instancia_Producto_UnitarioForm,
        "Instancia unitaria agregada",
        "lista_productos",
    )


@login_required
@administrador_requerido
def editar_instancia_unitaria(request, pk):
    instancia = get_object_or_404(Instancia_Producto_Unitario, pk=pk)
    return _render_form(
        request,
        Instancia_Producto_UnitarioForm,
        "Instancia unitaria modificada",
        "lista_productos",
        instance=instancia,
    )


@login_required
@administrador_requerido
def eliminar_instancia_unitaria(request, pk):
    instancia = get_object_or_404(Instancia_Producto_Unitario, pk=pk)
    return _confirm_delete(
        request,
        instancia,
        "lista_productos",
        "Instancia unitaria eliminada",
        "No se pudo eliminar la instancia unitaria.",
    )


@login_required
@administrador_requerido
def crear_instancia_peso(request):
    return _render_form(
        request,
        Instancia_Producto_PesoForm,
        "Instancia por peso agregada",
        "lista_productos",
    )


@login_required
@administrador_requerido
def editar_instancia_peso(request, pk):
    instancia = get_object_or_404(Instancia_Producto_Peso, pk=pk)
    return _render_form(
        request,
        Instancia_Producto_PesoForm,
        "Instancia por peso modificada",
        "lista_productos",
        instance=instancia,
    )


@login_required
@administrador_requerido
def eliminar_instancia_peso(request, pk):
    instancia = get_object_or_404(Instancia_Producto_Peso, pk=pk)
    return _confirm_delete(
        request,
        instancia,
        "lista_productos",
        "Instancia por peso eliminada",
        "No se pudo eliminar la instancia por peso.",
    )


@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, "categoria/categoria_list.html", {"categorias": categorias})


@login_required
@administrador_requerido
def crear_categoria(request):
    return _render_form(
        request,
        CategoriaForm,
        "Categoría agregada",
        "lista_categorias",
    )


@login_required
@administrador_requerido
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    return _render_form(
        request,
        CategoriaForm,
        "Categoría modificada",
        "lista_categorias",
        instance=categoria,
    )


@login_required
@administrador_requerido
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    return _confirm_delete(
        request,
        categoria,
        "lista_categorias",
        "Categoría eliminada",
        "No se puede eliminar la categoría porque tiene productos asociados.",
    )


@login_required
def lista_lotes(request):
    lotes = Lote.objects.all()
    return render(request, "lote/lote_list.html", {"lotes": lotes})


@login_required
@administrador_requerido
def crear_lote(request):
    return _render_form(
        request,
        LoteForm,
        "Lote agregado",
        "lista_lotes",
    )


@login_required
@administrador_requerido
def editar_lote(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    return _render_form(
        request,
        LoteForm,
        "Lote modificado",
        "lista_lotes",
        instance=lote,
    )


@login_required
@administrador_requerido
def eliminar_lote(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    deleted_instance_count = (
        lote.instancia_producto_unitario.count()
        + lote.instancia_producto_peso.count()
    )
    return _confirm_delete(
        request,
        lote,
        "lista_lotes",
        "Lote eliminado",
        "No se pudo eliminar el lote.",
        deleted_instance_count,
    )
