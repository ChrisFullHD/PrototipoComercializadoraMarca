from django import forms
from .models import Baja, Devolucion

class BajaForms(forms.ModelForm):
    MOTIVOS = [
        ('', 'Seleccione un motivo'),
        ('Producto vencido', 'Producto vencido'),
        ('Producto dañado', 'Producto dañado'),
        ('Defecto de fabricación', 'Defecto de fabricación'),
        ('Merma o pérdida', 'Merma o pérdida'),
        ('Producto retirado por seguridad', 'Producto retirado por seguridad'),
        ('Otro', 'Otro'),
    ]

    motivo = forms.ChoiceField(
        choices=MOTIVOS,
        label='Motivo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    motivo_personalizado = forms.CharField(
        label='Motivo personalizado',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el motivo',
        }),
    )

    class Meta:
        model = Baja
        fields = '__all__'
        labels = {
            'motivo': 'Motivo',
            'producto': 'Producto',
        }
        widgets = {'producto': forms.Select(attrs={'class': 'form-select'})}

class DevolucionForms(forms.ModelForm):
    MOTIVOS = [
        ('', 'Seleccione un motivo'),
        ('Producto defectuoso', 'Producto defectuoso'),
        ('Producto incompleto', 'Producto incompleto'),
        ('Cliente rechazó el producto', 'Cliente rechazó el producto'),
        ('Producto equivocado', 'Producto equivocado'),
        ('Devolución por garantía', 'Devolución por garantía'),
        ('Otro', 'Otro'),
    ]

    motivo = forms.ChoiceField(
        choices=MOTIVOS,
        label='Motivo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    motivo_personalizado = forms.CharField(
        label='Motivo personalizado',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el motivo',
        }),
    )

    class Meta:
        model = Devolucion
        fields = '__all__'
        labels = {
            'motivo': 'Motivo',
            'producto': 'Producto',
        }
        widgets = {'producto': forms.Select(attrs={'class': 'form-select'})}