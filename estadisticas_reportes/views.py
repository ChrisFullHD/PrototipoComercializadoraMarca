from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from ventas.models import Venta, Detalle_Venta
from inventario.models import Producto_Unitario, Instancia_Producto_Peso
from usuarios.models import Perfil


@login_required
def panel_estadisticas(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('')

    hoy = timezone.localdate()

    ventas_hoy = Venta.objects.filter(fecha_hora__date=hoy)
    total_recaudado = ventas_hoy.aggregate(total=Sum('total_venta'))['total'] or 0
    cantidad_ventas = ventas_hoy.count()

    productos_rotacion = (
        Detalle_Venta.objects
        .values('producto__nombre')
        .annotate(unidades_vendidas=Sum('cantidad_unidades'))
        .filter(unidades_vendidas__gt=0)
        .order_by('-unidades_vendidas', 'producto__nombre')[:10]
    )

    context = {
        'total_ventas': total_recaudado,
        'cantidad_ventas': cantidad_ventas,
        'productos_labels': [item['producto__nombre'] for item in productos_rotacion],
        'productos_valores': [item['unidades_vendidas'] for item in productos_rotacion],
    }
    return render(
        request,
        'estadisticas_reportes/estadisticas/estadisticas_panel.html',
        context,
    )


@login_required
def ventas_totales(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('')

    ventas = Venta.objects.all().order_by('-fecha_hora')
    periodo = 'dia'
    filtro_activo = None

    fecha = request.GET.get('fecha', '').strip()
    mes = request.GET.get('mes', '').strip()
    anio = request.GET.get('anio', '').strip()

    if fecha:
        periodo = 'dia'
        try:
            filtro_activo = datetime.strptime(fecha, '%Y-%m-%d').date()
            ventas = ventas.filter(fecha_hora__date=filtro_activo)
        except ValueError:
            filtro_activo = None
            ventas = Venta.objects.none()
    elif mes:
        periodo = 'mes'
        try:
            filtro_activo = datetime.strptime(mes, '%Y-%m').date()
            ventas = ventas.filter(
                fecha_hora__year=filtro_activo.year,
                fecha_hora__month=filtro_activo.month,
            )
        except ValueError:
            filtro_activo = None
            ventas = Venta.objects.none()
    elif anio:
        periodo = 'anio'
        try:
            filtro_activo = int(anio)
            ventas = ventas.filter(fecha_hora__year=filtro_activo)
        except (TypeError, ValueError):
            filtro_activo = None
            ventas = Venta.objects.none()
    else:
        hoy = timezone.localdate()
        ventas = ventas.filter(fecha_hora__date=hoy)
        filtro_activo = hoy

    total_ventas = ventas.aggregate(total=Sum('total_venta'))['total'] or 0

    return render(
        request,
        'estadisticas_reportes/ventas_totales/ventas_totales.html',
        {
            'ventas': ventas,
            'total_ventas': total_ventas,
            'cantidad_ventas': ventas.count(),
            'periodo': periodo,
            'filtro_activo': filtro_activo,
        },
    )


@login_required
def productos_mayor_rotacion(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('')

    productos = (
        Detalle_Venta.objects
        .values(
            'producto__id',
            'producto__codigo_barras',
            'producto__nombre',
            'producto__categoria__nombre',
        )
        .annotate(unidades_vendidas=Sum('cantidad_unidades'))
        .filter(unidades_vendidas__gt=0)
        .order_by('-unidades_vendidas', 'producto__nombre')
    )

    return render(
        request,
        'estadisticas_reportes/productos_mayor_rotacion/productos_mayor_rotacion.html',
        {'productos': productos},
    )


@login_required
def stock_productos(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    if perfil.rol.nombre != 'Administrador':
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('')

    productos = list(
        Producto_Unitario.objects
        .select_related('categoria')
        .order_by('nombre')
    )

    for producto in productos:
        producto.stock_kg = (
            Instancia_Producto_Peso.objects
            .filter(producto=producto)
            .aggregate(total=Sum('cantidad_kg'))['total']
            or Decimal('0')
        )

    total_unidades = sum(producto.unidades_stock for producto in productos)
    total_kg = sum(
        (producto.stock_kg or 0)
        for producto in productos
    )

    return render(
        request,
        'estadisticas_reportes/stock_productos/stock_productos.html',
        {
            'productos': productos,
            'total_unidades': total_unidades,
            'total_kg': total_kg,
            'total_productos': len(productos),
            'productos_bajo_stock': sum(
                1
                for producto in productos
                if producto.unidades_stock <= 5 and not producto.stock_kg
            ),
        },
    )
