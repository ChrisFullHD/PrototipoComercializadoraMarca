# Heredar el formulario de registro de Django
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Perfil, Rol


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Nombre de usuario o contraseña incorrectos.",
        "inactive": "Esta cuenta no está activa.",
    }


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
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        ]

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
    password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput,
        help_text="Déjala vacía para conservar la contraseña actual.",
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        perfil = Perfil.objects.filter(user=self.instance).first()
        if perfil:
            self.fields["rol"].initial = perfil.rol
        else:
            self.fields["rol"].initial = Rol.objects.filter(nombre="Empleado").first()

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif password1:
                try:
                    validate_password(password1, user=self.instance)
                except ValidationError as error:
                    self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            with transaction.atomic():
                password1 = self.cleaned_data.get("password1")
                if password1:
                    user.set_password(password1)
                user.save()
                Perfil.objects.update_or_create(
                    user=user,
                    defaults={"rol": self.cleaned_data["rol"]},
                )
        return user