from functools import wraps

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    CustomAuthenticationForm,
    CustomUserChangeForm,
    CustomUserCreationForm,
)
from .models import Perfil


def inicio_sitio(request):
    if request.user.is_authenticated:
        return redirect("registrar_venta")
    return redirect("iniciar_sesion")


def administrador_requerido(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        is_admin = request.user.is_superuser or Perfil.objects.filter(
            user=request.user,
            rol__nombre="Administrador",
        ).exists()
        if not is_admin:
            messages.error(request, "Solo un administrador puede gestionar usuarios.")
            return redirect("lista_productos")
        return view_func(request, *args, **kwargs)

    return wrapped_view


def _render_user_form(request, form_class, page_title, instance=None):
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"OperaciÃ³n '{page_title}' realizada correctamente.")
        return redirect("lista_usuarios")

    return render(
        request,
        "usuarios/usuario_form.html",
        {
            "form": form,
            "page_title": page_title,
            "cancel_url": "lista_usuarios",
        },
    )


def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()
    form = CustomAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = settings.LOGIN_REDIRECT_URL
        return redirect(next_url)

    return render(request, "usuarios/login.html", {"form": form, "next": next_url})


def cerrar_sesion(request):
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    logout(request)
    return redirect("iniciar_sesion")


@login_required
@administrador_requerido
def lista_usuarios(request):
    usuarios = User.objects.select_related("perfil", "perfil__rol").order_by(
        "username"
    )
    return render(request, "usuarios/usuario_list.html", {"usuarios": usuarios})


@login_required
@administrador_requerido
def crear_usuario(request):
    return _render_user_form(request, CustomUserCreationForm, "Agregar un usuario")


@login_required
@administrador_requerido
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    return _render_user_form(
        request,
        CustomUserChangeForm,
        "Modificar datos de usuario",
        instance=usuario,
    )


@login_required
@administrador_requerido
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect("lista_usuarios")

    if request.method == "POST":
        usuario.delete()
        messages.success(request, "Usuario eliminado correctamente.")
        return redirect("lista_usuarios")

    return render(
        request,
        "usuarios/usuario_confirm_delete.html",
        {
            "obj": usuario,
            "form": forms.Form(),
            "cancel_url": "lista_usuarios",
        },
    )