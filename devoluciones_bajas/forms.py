from django import forms
from .models import Baja, Devolucion

class BajaForms(forms.ModelForm):
    class Meta:
        model = Baja
        fields = '__all__'
        labels = {
            'motivo': 'Motivo',
            'producto': 'Producto',
        }
        widgets = {
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describa el motivo de la baja',
            }),
            'producto': forms.Select(attrs={'class': 'form-select'}),
        }

class DevolucionForms(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = '__all__'
        labels = {
            'motivo': 'Motivo',
            'producto': 'Producto',
        }
        widgets = {
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describa el motivo de la devolución',
            }),
            'producto': forms.Select(attrs={'class': 'form-select'}),
        }