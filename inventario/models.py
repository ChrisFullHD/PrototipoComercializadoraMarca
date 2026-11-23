from django.db import models
from django.core.validators import MinValueValidator
from usuarios.models import Perfil

class Categoria(models.Model):
    nombre = models.CharField(max_length=50, verbose_name="Nombre de categoría", unique=True)

    def __str__(self):
        return self.nombre

class Lote(models.Model):
    numero_lote = models.CharField(max_length=30, verbose_name="Número/Código de lote")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de vencimiento")

    def __str__(self):
        return f'{self.numero_lote} - {self.fecha_vencimiento}'

class Producto(models.Model):
    codigo_barras = models.CharField(
        max_length=100,
        verbose_name="Código de barras",
        unique=True,
        blank=True,
        null=True,
    )
    nombre = models.CharField(max_length=80, verbose_name="Nombre del producto", unique=True)
    imagen = models.ImageField(verbose_name="Imagen del producto", blank=True, null=True, upload_to="productos")
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT, related_name="productos")

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.codigo_barras or "Sin código"} - {self.nombre}'

class Producto_Unitario(Producto):
    unidades_stock = models.PositiveIntegerField(verbose_name="Cantidad unidades en stock", validators=[MinValueValidator(0)], default=0)
    peso_kg = models.DecimalField(verbose_name="Peso producto unitario en Kg", validators=[MinValueValidator(0.0)], max_digits=10, decimal_places=4)
    precio_compra_unidad = models.PositiveIntegerField(verbose_name="Precio de compra distribuidor", validators=[MinValueValidator(0)], default=0)
    precio_venta_unidad = models.PositiveIntegerField(verbose_name="Precio de venta", validators=[MinValueValidator(0)], default=0)

class Instancia_Producto_Peso(models.Model):
    producto = models.ForeignKey(Producto_Unitario, on_delete=models.CASCADE, related_name="instancia_producto_peso")
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="instancia_producto_peso")
    cantidad_kg = models.DecimalField(verbose_name="Cantidad en Kg", validators=[MinValueValidator(0.0)], max_digits=10, decimal_places=4, default=0.0)
    precio_kg = models.PositiveIntegerField(verbose_name="Precio por Kg", validators=[MinValueValidator(0)], default=0)
    merma_acumulada_kg = models.DecimalField(verbose_name="Merma acumulada en Kg", validators=[MinValueValidator(0.0)], max_digits=10, decimal_places=4, default=0.0)

    def __str__(self):
        codigo = self.producto.codigo_barras or "Sin código"
        return f'{codigo} - {self.lote.numero_lote} - {self.producto.nombre}'

class Instancia_Producto_Unitario(models.Model):
    producto = models.ForeignKey(Producto_Unitario, on_delete=models.CASCADE, related_name="instancia_producto_unitario")
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="instancia_producto_unitario")

    def __str__(self):
        codigo = self.producto.codigo_barras or "Sin código"
        return f'{codigo} - {self.lote.numero_lote} - {self.producto.nombre}'

# Operaciones: Agrega - Modifica - Elimina
class Movimientos_Inventario(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Realizado a las")

    # Registros asociados a un perfil de usuario, si se elimina, se conserva evidencia en texto (nombre_perfil_historico, nombre_producto_historico)
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    producto = models.ForeignKey(Producto_Unitario, on_delete=models.SET_NULL, null=True, blank=True)

    nombre_perfil_historico = models.CharField(max_length=150, blank=True)
    nombre_producto_historico = models.CharField(max_length=150, blank=True)

    operacion = models.CharField(max_length=10)

    def save(self, *args, **kwargs):
        if self.perfil and not self.nombre_perfil_historico:
            self.nombre_perfil_historico = str(self.perfil)
        if self.producto and not self.nombre_producto_historico:
            self.nombre_producto_historico = str(self.producto)
        super().save(*args, **kwargs)

    def __str__(self):
        usuario = self.perfil.user.user if self.perfil else f"{self.nombre_perfil_historico} (Eliminado)"
        prod = self.producto if self.producto else f"{self.nombre_producto_historico} (Eliminado)"
        return f"{self.fecha_hora} - {usuario} - {prod} ({self.operacion})"