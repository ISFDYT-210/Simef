"""
Recorre todas las rutas del sistema sin sesión iniciada (SEC-10).

Cada ruta se pide por GET y por POST como visitante anónimo. Solo las páginas
de RUTAS_PUBLICAS pueden responder con contenido; cualquier otra tiene que
mandar al login, negar el acceso o no existir. Ninguna puede dar error 500.

La lista de rutas sale de las URLs registradas, así que una ruta nueva entra
sola en el test: si se agrega sin login_required ni capacidad_requerida, este
test falla hasta que se la proteja o se la sume a RUTAS_PUBLICAS con su motivo.
"""
import re
import uuid

from django.conf import settings
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RoutePattern

# Ruta (tal como está en urls.py) -> por qué puede verse sin sesión.
RUTAS_PUBLICAS = {
    '': 'Página de inicio, con el acceso al login',
    'accounts/login/': 'Formulario de inicio de sesión',
    'accounts/logout/': 'Cerrar sesión; sin sesión solo redirige al inicio',
    'recuperar_pass/': 'Pedir el enlace para recuperar la contraseña por DNI',
    'accounts/password_reset/': 'Recuperar contraseña (vista estándar de Django)',
    'accounts/password_reset/done/': 'Aviso de que se envió el enlace',
    'accounts/reset/<uidb64>/<token>/': 'Enlace del email; sin token válido no deja cambiar nada',
    'accounts/reset/done/': 'Aviso de contraseña cambiada',
    'password_reset/done/': 'Aviso de que se envió el enlace',
    'reset/<uidb64>/<token>/': 'Enlace del email; sin token válido no deja cambiar nada',
    'reset/done/': 'Aviso de contraseña cambiada',
}

# Valor de ejemplo para cada tipo de parámetro de las rutas.
VALORES_DE_EJEMPLO = {
    'int': '1',
    'str': 'x',
    'slug': 'x',
    'path': 'x',
    'uuid': str(uuid.uuid4()),
}


def _rutas(patrones=None, prefijo=''):
    """Devuelve (ruta, url) de cada ruta registrada, fuera del admin de Django."""
    if patrones is None:
        patrones = get_resolver().url_patterns
    for patron in patrones:
        if isinstance(patron, URLResolver):
            if patron.namespace == 'admin':
                continue  # se prueba aparte, en test_admin_pide_login
            yield from _rutas(patron.url_patterns, prefijo + str(patron.pattern))
        elif isinstance(patron, URLPattern):
            ruta = prefijo + str(patron.pattern)
            if not isinstance(patron.pattern, RoutePattern):
                raise AssertionError(
                    f'La ruta {ruta!r} usa una expresión regular; '
                    'agregá cómo armar su URL de ejemplo en este test.'
                )
            url = re.sub(
                r'<(?:(\w+):)?\w+>',
                lambda m: VALORES_DE_EJEMPLO[m.group(1) or 'str'],
                ruta,
            )
            yield ruta, '/' + url


class RutasSinSesionTest(TestCase):

    def test_hay_rutas_para_recorrer(self):
        rutas = dict(_rutas())
        self.assertGreater(len(rutas), 50)
        for publica in RUTAS_PUBLICAS:
            self.assertIn(publica, rutas, f'{publica!r} ya no existe: sacala de RUTAS_PUBLICAS')

    def test_ninguna_ruta_privada_responde_sin_sesion(self):
        for ruta, url in _rutas():
            if ruta in RUTAS_PUBLICAS:
                continue
            for metodo in ('get', 'post'):
                with self.subTest(ruta=ruta, metodo=metodo.upper()):
                    respuesta = getattr(self.client, metodo)(url)
                    if respuesta.status_code == 302:
                        self.assertTrue(
                            respuesta.url.startswith(settings.LOGIN_URL),
                            f'{url} redirige a {respuesta.url}, no al login',
                        )
                    else:
                        self.assertIn(
                            respuesta.status_code, (403, 404, 405),
                            f'{url} responde {respuesta.status_code} sin sesión',
                        )

    def test_las_rutas_publicas_no_fallan(self):
        for ruta, url in _rutas():
            if ruta not in RUTAS_PUBLICAS:
                continue
            for metodo in ('get', 'post'):
                with self.subTest(ruta=ruta, metodo=metodo.upper()):
                    respuesta = getattr(self.client, metodo)(url)
                    self.assertLess(respuesta.status_code, 500, url)

    def test_admin_pide_login(self):
        # Con el admin habilitado (desarrollo y tests) manda a su propio login;
        # en producción ni existe: redirige al inicio (ver test_settings.py).
        respuesta = self.client.get('/admin/')
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta.url)
