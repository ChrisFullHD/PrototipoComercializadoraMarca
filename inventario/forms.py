from django import forms
from .models import Categoria, Lote, Producto_Unitario, Instancia_Producto_Peso, Instancia_Producto_Unitario

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = '__all__'

class Producto_UnitarioForm(forms.ModelForm):
    class Meta:
        model = Producto_Unitario
        fields = '__all__'

class Instancia_Producto_PesoForm(forms.ModelForm):
    class Meta:
        model = Instancia_Producto_Peso
        fields = '__all__'

class Instancia_Producto_UnitarioForm(forms.ModelForm):
    class Meta:
        model = Instancia_Producto_Unitario
        fields = '__all__'