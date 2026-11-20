# Heredar el formulario de registro de Django
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import Perfil, Rol


# Formulario utilizado únicamente por el Administrador para crear usuarios
class CustomUserCreationForm(UserCreationForm):
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.order_by("nombre"),
        empty_label=None,
        label="Rol del usuario",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            rol_default = Rol.objects.filter(nombre="Empleado").first()
            if rol_default:
                self.fields["rol"].initial = rol_default

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "password1"]

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            with transaction.atomic():
                user.save()
                Perfil.objects.create(user=user, rol=self.cleaned_data["rol"])
        return user


class CustomUserChangeForm(forms.ModelForm):
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.order_by("nombre"),
        empty_label=None,
        label="Rol del usuario",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        perfil = Perfil.objects.filter(user=self.instance).first()
        if perfil:
            self.fields["rol"].initial = perfil.rol
        else:
            self.fields["rol"].initial = Rol.objects.filter(nombre="Empleado").first()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            with transaction.atomic():
                user.save()
                Perfil.objects.update_or_create(
                    user=user,
                    defaults={"rol": self.cleaned_data["rol"]},
                )
        return user