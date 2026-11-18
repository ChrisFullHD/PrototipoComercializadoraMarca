from django import forms
from .models import Respaldos

class RespaldoForms(forms.ModelForm):
    class Meta:
        model = Respaldos
        fields = '__all__'