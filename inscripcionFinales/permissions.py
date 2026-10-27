"""
Control de acceso por rol y capacidades para SIMEF.

Centraliza "quién puede hacer qué":
 - capacidad_requerida(...)  -> vistas-función (chequea capacidades)
 - rol_requerido(...)        -> vistas-función (chequea rol directo)
 - super_admin_requerido     -> solo super administrador
 - CapacidadRequeridaMixin   -> vistas basadas en clase (CBV)
"""
from functools import wraps
from django.shortcuts import render
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def _denegar(request):
    """Muestra la página 403 propia con estado HTTP 403."""
    return render(request, '403_forbidden.html', status=403)


def capacidad_requerida(*capacidades):
    """
    Deja pasar si el usuario tiene AL MENOS UNA de las capacidades.
    Ej:
        @capacidad_requerida('gestionar_usuarios')
        def alta_usuario(request): ...
    """
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if any(request.user.tiene_capacidad(c) for c in capacidades):
                return view_func(request, *args, **kwargs)
            return _denegar(request)
        return _wrapped
    return decorador


def rol_requerido(*roles):
    """Deja pasar si el rol del usuario está en la lista (o es super admin)."""
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.is_superuser or request.user.rol in roles:
                return view_func(request, *args, **kwargs)
            return _denegar(request)
        return _wrapped
    return decorador


def super_admin_requerido(view_func):
    """Solo el super administrador puede entrar."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return _denegar(request)
    return _wrapped


class CapacidadRequeridaMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Para vistas basadas en clase. Definir 'capacidades_requeridas'.
    Ej:
        class ListaUsuarios(CapacidadRequeridaMixin, ListView):
            capacidades_requeridas = ('gestionar_usuarios',)
    """
    capacidades_requeridas = ()

    def test_func(self):
        usuario = self.request.user
        return any(usuario.tiene_capacidad(c) for c in self.capacidades_requeridas)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()   # manda al login
        return render(self.request, '403_forbidden.html', status=403)