# Heredar el formulario de registro de Django
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil, Rol

# Formulario utilizado únicamente por el Administrador para crear usuarios
class CustomUserCreationForm(UserCreationForm):

    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        empty_label=None,
        label='Rol del usuario',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            rol_default = Rol.objects.filter(nombre="Empleado").first()

            if rol_default:
                self.fields['rol'].initial = rol_default    

    class Meta:
        model = User
        # Nombre de usuario - Contraseña
        fields = ['first_name', 'last_name', 'username', 'password1']

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()
            Perfil.objects.create(
                user=user,
                rol=self.cleaned_data['rol']
            )
        return user