from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import ProtectedError
from .models import Devolucion, Baja
from .forms import DevolucionForms, BajaForms
from usuarios.models import Perfil
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def lista_devoluciones(request):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('')
    
    devolucion = Devolucion.objects.all().order_by('-pk')
    return render(request, 'devoluciones_bajas/devoluciones/devoluciones_list.html', {'object_list': devolucion})

@login_required
def lista_bajas(request):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    baja = Baja.objects.all().order_by('-pk')
    return render(request, 'devoluciones_bajas/bajas/bajas_list.html', {'object_list': baja})

@login_required
def crear_devolucion(request):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    form = DevolucionForms(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            personalizado = form.cleaned_data['motivo_personalizado'].strip()

            if motivo == 'Otro':
                if not personalizado:
                    form.add_error(
                        'motivo_personalizado',
                        'Debe especificar el motivo personalizado.',
                    )
                else:
                    form.cleaned_data['motivo'] = personalizado
                    form.save()
                    messages.success(request, 'Devolución creada correctamente.')
                    return redirect('lista_devoluciones')
            else:
                form.save()
                messages.success(request, 'Devolución creada correctamente.')
                return redirect('lista_devoluciones')
    return render(request, 'devoluciones_bajas/devoluciones/devoluciones_form.html', {'form': form, 'accion': 'Crear'})

@login_required
def crear_baja(request):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    form = BajaForms(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            personalizado = form.cleaned_data['motivo_personalizado'].strip()

            if motivo == 'Otro':
                if not personalizado:
                    form.add_error(
                        'motivo_personalizado',
                        'Debe especificar el motivo personalizado.',
                    )
                else:
                    form.cleaned_data['motivo'] = personalizado
                    form.save()
                    messages.success(request, 'Baja de producto creada correctamente.')
                    return redirect('lista_bajas')
            else:
                form.save()
                messages.success(request, 'Baja de producto creada correctamente.')
                return redirect('lista_bajas')
    return render(request, 'devoluciones_bajas/bajas/bajas_form.html', {'form': form, 'accion': 'Crear'})

@login_required
def detalle_devolucion(request, pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    devolucion = get_object_or_404(Devolucion,pk=pk)
    return render(request, 'devoluciones_bajas/devoluciones/devoluciones_detail.html', {'object': devolucion})

@login_required
def detalle_baja(request, pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    baja = get_object_or_404(Baja, pk=pk)
    return render(request, 'devoluciones_bajas/bajas/bajas_detail.html', {'object': baja})

@login_required 
def eliminar_devolucion(request, pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    devolucion = get_object_or_404(Devolucion, pk=pk)

    if request.method == 'POST':
        try:
            devolucion.delete()
            messages.success(request, 'Devolución eliminada correctamente.')
            return redirect('lista_devoluciones')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar la devolución porque está asociada a otros registros.')
    return render(request, 'devoluciones_bajas/devoluciones/devoluciones_delete.html', {'object': devolucion})

@login_required
def eliminar_baja(request,pk):
    perfil = get_object_or_404(Perfil, user = request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect()
    
    baja = get_object_or_404(Baja, pk=pk)

    if request.method == 'POST':
        try:
            baja.delete()
            messages.success(request, 'Baja de producto eliminada correctamente.')
            return redirect('lista_bajas')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar la baja porque está asociada a otros registros.')
            return redirect('detalle_baja', pk=pk)
    return render(request, 'devoluciones_bajas/bajas/bajas_delete.html', {'object': baja})