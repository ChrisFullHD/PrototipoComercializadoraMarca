from django import forms
from .models import Baja, Devolucion

class BajaForms(forms.ModelForm):
    class Meta:
        model = Baja
        fields = '__all__'

class DevolucionForms(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = '__all__'