from django import forms
from .models import Venta, Detalle_Venta, VentaFiada


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['medio_pago', 'total_venta']


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = Detalle_Venta
        fields = [
            'producto',
            'instancia_peso',
            'tipo_item',
            'cantidad_unidades',
            'cantidad_kg',
            'precio_unitario',
            'subtotal',
        ]


class VentaFiadaForm(forms.ModelForm):
    class Meta:
        model = VentaFiada
        fields = [
            'cliente_nombre',
            'cliente_telefono',
            'fecha_vencimiento',
            'estado',
            'detalle',
        ]
        widgets = {'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'})}