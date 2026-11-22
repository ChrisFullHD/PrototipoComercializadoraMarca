from datetime import date
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, F
from inventario.models import Producto_Unitario, Instancia_Producto_Peso
from .models import Venta, Detalle_Venta, VentaFiada
from .forms import VentaFiadaForm


def _calcular_saldo_fiado(venta_fiada):
    saldo = int(venta_fiada.monto_fiado) - int(venta_fiada.abono_inicial)
    return saldo if saldo > 0 else 0


@login_required
def lista_ventas(request):
    q = request.GET.get('q', '').strip()
    ventas = Venta.objects.select_related('usuario').prefetch_related('detalles__producto').order_by('-fecha_hora')

    if q:
        medios_pago_coincidentes = [
            codigo
            for codigo, etiqueta in Venta.MEDIO_PAGO
            if q.lower() in etiqueta.lower() or etiqueta.lower() in q.lower()
        ]
        ventas = ventas.filter(
            Q(id__icontains=q)
            | Q(medio_pago__icontains=q)
            | Q(medio_pago__in=medios_pago_coincidentes)
            | Q(usuario__username__icontains=q)
            | Q(detalles__producto__nombre__icontains=q)
            | Q(detalles__producto__codigo_barras__icontains=q)
        ).distinct()

    total_recaudado = ventas.aggregate(total=Sum('total_venta'))['total'] or 0
    return render(
        request,
        'ventas/venta_list.html',
        {
            'ventas': ventas,
            'q': q,
            'total_recaudado': total_recaudado,
        },
    )


@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related('usuario').prefetch_related('detalles__producto', 'detalles__instancia_peso'),
        pk=pk,
    )
    return render(request, 'ventas/venta_detail.html', {'venta': venta})


@login_required
def registrar_venta(request):
    productos_unidad = Producto_Unitario.objects.filter(unidades_stock__gt=0).order_by('nombre')
    instancias_peso = (
        Instancia_Producto_Peso.objects.select_related('producto', 'lote')
        .filter(cantidad_kg__gt=0)
        .order_by('producto__nombre', 'lote__fecha_vencimiento')
    )

    if request.method == 'POST':
        medio_pago = request.POST.get('medio_pago', 'EFE')
        medios_pago_validos = {codigo for codigo, _ in Venta.MEDIO_PAGO}
        if medio_pago not in medios_pago_validos:
            messages.error(request, 'Selecciona un medio de pago válido.')
            return redirect('registrar_venta')

        es_fiado = (medio_pago == 'FIA')

        cliente_nombre = request.POST.get('cliente_nombre', '').strip()
        cliente_telefono = request.POST.get('cliente_telefono', '').strip()
        detalle_fiado = request.POST.get('detalle_fiado', '').strip()
        fecha_vencimiento_str = request.POST.get('fecha_vencimiento', '').strip()
        abono_inicial_str = request.POST.get('abono_inicial', '0').strip()

        if es_fiado and not cliente_nombre:
            messages.error(request, 'Debes ingresar el nombre del cliente para registrar una venta fiada.')
            return render(
                request,
                'ventas/venta_form.html',
                {
                    'productos_unidad': productos_unidad,
                    'instancias_peso': instancias_peso,
                    'medios_pago': Venta.MEDIO_PAGO,
                    'cliente_nombre': cliente_nombre,
                    'cliente_telefono': cliente_telefono,
                    'abono_inicial': abono_inicial_str or '0',
                    'fecha_vencimiento': fecha_vencimiento_str,
                    'detalle_fiado': detalle_fiado,
                },
            )

        try:
            abono_inicial = Decimal(abono_inicial_str or '0')
            if abono_inicial < 0:
                abono_inicial = Decimal('0')
        except InvalidOperation:
            abono_inicial = Decimal('0')

        fecha_vencimiento = None
        if fecha_vencimiento_str:
            try:
                fecha_vencimiento = date.fromisoformat(fecha_vencimiento_str)
            except ValueError:
                fecha_vencimiento = None

        items_data = []
        total_venta = 0

        # Procesar productos por unidad enviados desde el formulario
        producto_ids = request.POST.getlist('producto_unidad_id')
        cantidades_unidad = request.POST.getlist('cantidad_unidad')

        for prod_id, cant_str in zip(producto_ids, cantidades_unidad):
            if not prod_id or not cant_str:
                continue
            try:
                cantidad = int(cant_str)
            except ValueError:
                messages.error(request, 'La cantidad en unidades debe ser un número entero válido.')
                return redirect('registrar_venta')

            if cantidad <= 0:
                continue

            producto = get_object_or_404(Producto_Unitario, pk=prod_id)
            if cantidad > producto.unidades_stock:
                messages.error(
                    request,
                    f'Stock insuficiente para "{producto.nombre}" (disponible: {producto.unidades_stock} unidades).',
                )
                return redirect('registrar_venta')

            subtotal = int(producto.precio_venta_unidad * cantidad)
            total_venta += subtotal
            items_data.append({
                'tipo_item': 'UNI',
                'producto': producto,
                'instancia_peso': None,
                'cantidad_unidades': cantidad,
                'cantidad_kg': Decimal('0.0000'),
                'precio_unitario': producto.precio_venta_unidad,
                'subtotal': subtotal,
            })

        # Procesar productos por peso enviados desde el formulario
        instancia_ids = request.POST.getlist('instancia_peso_id')
        cantidades_kg = request.POST.getlist('cantidad_kg')

        for inst_id, kg_str in zip(instancia_ids, cantidades_kg):
            if not inst_id or not kg_str:
                continue
            try:
                kg = Decimal(kg_str.replace(',', '.'))
            except Exception:
                messages.error(request, 'El peso ingresado no es válido.')
                return redirect('registrar_venta')

            if kg <= Decimal('0'):
                continue

            instancia = get_object_or_404(
                Instancia_Producto_Peso.objects.select_related('producto'),
                pk=inst_id,
            )
            if kg > instancia.cantidad_kg:
                messages.error(
                    request,
                    f'Stock insuficiente en peso para "{instancia.producto.nombre}" (disponible: {instancia.cantidad_kg} kg).',
                )
                return redirect('registrar_venta')

            subtotal = int(round(Decimal(instancia.precio_kg) * kg))
            total_venta += subtotal
            items_data.append({
                'tipo_item': 'PES',
                'producto': instancia.producto,
                'instancia_peso': instancia,
                'cantidad_unidades': 0,
                'cantidad_kg': kg,
                'precio_unitario': instancia.precio_kg,
                'subtotal': subtotal,
            })

        if not items_data:
            messages.error(request, 'Debes agregar al menos un producto con cantidad válida para registrar la venta.')
            return redirect('registrar_venta')

        with transaction.atomic():
            venta = Venta.objects.create(
                usuario=request.user,
                medio_pago=medio_pago,
                total_venta=total_venta,
            )

            for item in items_data:
                Detalle_Venta.objects.create(
                    venta=venta,
                    producto=item['producto'],
                    instancia_peso=item['instancia_peso'],
                    tipo_item=item['tipo_item'],
                    cantidad_unidades=item['cantidad_unidades'],
                    cantidad_kg=item['cantidad_kg'],
                    precio_unitario=item['precio_unitario'],
                    subtotal=item['subtotal'],
                )

                if item['tipo_item'] == 'UNI':
                    Producto_Unitario.objects.filter(pk=item['producto'].pk).update(
                        unidades_stock=F('unidades_stock') - item['cantidad_unidades']
                    )
                elif item['tipo_item'] == 'PES' and item['instancia_peso'] is not None:
                    Instancia_Producto_Peso.objects.filter(pk=item['instancia_peso'].pk).update(
                        cantidad_kg=F('cantidad_kg') - item['cantidad_kg']
                    )

            if es_fiado:
                monto_total = Decimal(str(venta.total_venta))
                abono_aplicado = min(abono_inicial, monto_total)
                if abono_aplicado < 0:
                    abono_aplicado = Decimal('0')

                if abono_aplicado >= monto_total and monto_total > 0:
                    estado_fiado = 'PAG'
                elif abono_aplicado > 0:
                    estado_fiado = 'PAR'
                else:
                    estado_fiado = 'PEN'

                VentaFiada.objects.create(
                    venta=venta,
                    fecha_venta=date.today(),
                    cliente_nombre=cliente_nombre,
                    cliente_telefono=cliente_telefono,
                    monto_fiado=monto_total,
                    abono_inicial=abono_aplicado,
                    fecha_vencimiento=fecha_vencimiento,
                    estado=estado_fiado,
                    detalle=detalle_fiado,
                    usuario=request.user,
                )

        messages.success(request, f'Venta #{venta.id} registrada correctamente por ${venta.total_venta}.')
        return redirect('detalle_venta', pk=venta.id)

    return render(
        request,
        'ventas/venta_form.html',
        {
            'productos_unidad': productos_unidad,
            'instancias_peso': instancias_peso,
            'medios_pago': Venta.MEDIO_PAGO,
        },
    )


@login_required
def lista_ventas_fiadas(request):
    q = request.GET.get('q', '').strip()
    fiadas = VentaFiada.objects.select_related('usuario', 'venta').order_by('-fecha_venta', '-id')

    if q:
        filtros = Q(cliente_nombre__icontains=q) | Q(cliente_telefono__icontains=q)
        if q.isdigit():
            filtros |= Q(id=int(q))
        fiadas = fiadas.filter(filtros)

    fiadas_con_saldo = []
    total_pendiente = 0
    ventas_por_cobrar = 0
    clientes_deudores = set()

    for f in fiadas:
        saldo = _calcular_saldo_fiado(f)
        fiadas_con_saldo.append({
            'obj': f,
            'saldo_pendiente': saldo,
        })
        if f.estado != 'PAG' and saldo > 0:
            total_pendiente += saldo
            ventas_por_cobrar += 1
            clientes_deudores.add(f.cliente_nombre.strip().lower())

    return render(
        request,
        'ventas/venta_fiada_list.html',
        {
            'fiadas_con_saldo': fiadas_con_saldo,
            'q': q,
            'total_pendiente': total_pendiente,
            'ventas_por_cobrar': ventas_por_cobrar,
            'clientes_deudores_count': len(clientes_deudores),
        },
    )


@login_required
def editar_venta_fiada(request, pk):
    fiada = get_object_or_404(VentaFiada, pk=pk)
    form = VentaFiadaForm(request.POST or None, instance=fiada)
    if request.method == 'POST':
        if form.is_valid():
            fiada_editada = form.save(commit=False)
            if _calcular_saldo_fiado(fiada_editada) == 0:
                fiada_editada.estado = 'PAG'
            fiada_editada.save()
            messages.success(request, 'Venta fiada actualizada correctamente.')
            return redirect('lista_ventas_fiadas')

    saldo_pendiente = _calcular_saldo_fiado(fiada)
    return render(
        request,
        'ventas/venta_fiada_form.html',
        {
            'form': form,
            'accion': 'Editar',
            'fiada': fiada,
            'saldo_pendiente': saldo_pendiente,
        },
    )


@login_required
def detalle_venta_fiada(request, pk):
    fiada = get_object_or_404(VentaFiada.objects.select_related('usuario', 'venta'), pk=pk)
    saldo_pendiente = _calcular_saldo_fiado(fiada)
    return render(
        request,
        'ventas/venta_fiada_detail.html',
        {'obj': fiada, 'saldo_pendiente': saldo_pendiente},
    )


@login_required
def eliminar_venta(request, pk):
    venta = get_object_or_404(
        Venta.objects.prefetch_related('detalles__producto', 'detalles__instancia_peso'),
        pk=pk,
    )
    if request.method == 'POST':
        with transaction.atomic():
            for det in venta.detalles.all():
                if det.tipo_item == 'UNI':
                    Producto_Unitario.objects.filter(pk=det.producto.pk).update(
                        unidades_stock=F('unidades_stock') + det.cantidad_unidades
                    )
                elif det.tipo_item == 'PES' and det.instancia_peso is not None:
                    Instancia_Producto_Peso.objects.filter(pk=det.instancia_peso.pk).update(
                        cantidad_kg=F('cantidad_kg') + det.cantidad_kg
                    )
            venta.delete()
        messages.success(request, f'Venta #{pk} eliminada y stock actualizado correctamente.')
        return redirect('lista_ventas')

    return render(request, 'ventas/venta_delete.html', {'obj': venta})


@login_required
def eliminar_venta_fiada(request, pk):
    fiada = get_object_or_404(VentaFiada, pk=pk)
    if request.method == 'POST':
        fiada.delete()
        messages.success(request, 'Venta fiada eliminada correctamente.')
        return redirect('lista_ventas_fiadas')
    return render(request, 'ventas/venta_fiada_delete.html', {'obj': fiada})