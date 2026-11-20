from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Proveedor
from .forms import ProveedorForm
from usuarios.models import Perfil


# Create your views here.
#PROVEEDORES
@login_required
def lista_proveedores(request):
    #obtener el texto de busqueda, si no hay queda vacio
    q = request.GET.get('q', '')
    #obtener todos los proveedores de la bd
    proveedores = Proveedor.objects.all()
    if q:
        #filtrar por nombre de fantasia o razon social sin importar mayusculas
        proveedores = proveedores.filter(
            Q(nombre_fantasia__icontains=q) | Q(razon_social__icontains=q)
        )
    return render(request, 'proveedores/proveedor_list.html', {'proveedores': proveedores, 'q': q})

@login_required
def crear_proveedores(request):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('lista_proveedores')
    
    form = ProveedorForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            #si es valido se guarda el nuevo registro
            form.save()
            messages.success(request, 'Proveedor creado correctamente.')
            return redirect('lista_proveedores')
    #sino se renderiza al formulario del proveedor
    return render(request, 'proveedores/proveedor_form.html', {'form': form, 'accion': 'Crear'})

@login_required
def editar_proveedores(request, pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('lista_proveedores')
    
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == 'POST':
        if form.is_valid():
            #si es valido se actualiza el registro
            form.save()
            messages.success(request, 'Proveedor actualizado correctamente.')
            return redirect('lista_proveedores')
    #sino se renderiza al formulario del proveedor
    return render(request, 'proveedores/proveedor_form.html', {'form': form, 'accion': 'Editar'})

@login_required
def eliminar_proveedores(request, pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('lista_proveedores')

    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        #se elimina el proveedor
        proveedor.delete()
        messages.success(request, 'Proveedor eliminado correctamente.')
        return redirect('lista_proveedores')
    #sino se renderiza a eliminar proveedor
    return render(request, 'proveedores/proveedor_delete.html', {'obj': proveedor})

@login_required
def detalle_proveedores(request, pk):
    #obtener el proveedor por su id, si no existe muestra error 404
    proveedor = get_object_or_404(Proveedor, pk=pk)
    return render(request, 'proveedores/proveedor_detail.html', {'obj': proveedor})