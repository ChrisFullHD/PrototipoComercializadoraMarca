from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from inventario.models import Producto_Unitario, Instancia_Producto_Peso


class Venta(models.Model):
    MEDIO_PAGO = [
        ('EFE', 'Efectivo'),
        ('DEB', 'Débito'),
        ('CRE', 'Crédito'),
        ('TRA', 'Transferencia'),
        ('FIA', 'Fiado'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Usuario'
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora'
    )
    medio_pago = models.CharField(
        max_length=3,
        choices=MEDIO_PAGO,
        default='EFE',
        verbose_name='Medio de pago'
    )
    total_venta = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Total de la venta'
    )

    def __str__(self):
        return f'Venta #{self.id} - ${self.total_venta}'


class Detalle_Venta(models.Model):
    TIPO_ITEM = [
        ('UNI', 'Por unidad'),
        ('PES', 'Por peso'),
    ]

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Venta'
    )
    producto = models.ForeignKey(
        Producto_Unitario,
        on_delete=models.PROTECT,
        related_name='detalles_venta',
        verbose_name='Producto'
    )
    instancia_peso = models.ForeignKey(
        Instancia_Producto_Peso,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='detalles_venta',
        verbose_name='Instancia por peso'
    )
    tipo_item = models.CharField(
        max_length=3,
        choices=TIPO_ITEM,
        default='UNI',
        verbose_name='Tipo de ítem'
    )
    cantidad_unidades = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Cantidad (unidades)'
    )
    cantidad_kg = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000'))],
        verbose_name='Cantidad (kg)'
    )
    precio_unitario = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Precio aplicado'
    )
    subtotal = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Subtotal'
    )

    def __str__(self):
        return f'{self.producto.nombre} - ${self.subtotal}'


class VentaFiada(models.Model):
    ESTADO_FIADO = [
        ('PEN', 'Pendiente'),
        ('PAR', 'Abono parcial'),
        ('PAG', 'Pagada'),
    ]

    venta = models.OneToOneField(
        Venta,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='venta_fiada',
        verbose_name='Venta asociada'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas_fiadas',
        verbose_name='Registrado por'
    )
    fecha_venta = models.DateField(
        verbose_name='Fecha de la venta'
    )
    cliente_nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre del cliente'
    )
    cliente_telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono del cliente'
    )
    monto_fiado = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Monto fiado'
    )
    abono_inicial = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Abono inicial'
    )
    fecha_vencimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha acordada de pago'
    )
    estado = models.CharField(
        max_length=3,
        choices=ESTADO_FIADO,
        default='PEN',
        verbose_name='Estado'
    )
    detalle = models.TextField(
        blank=True,
        verbose_name='Detalle / observaciones'
    )

    def __str__(self):
        return f'Venta fiada #{self.id} - {self.cliente_nombre}'