"""
Tests de la configuración de seguridad de settings.py (CICD-01, CICD-02, CICD-03, CICD-07).

El CI fija DEBUG='False' y carga todas las variables en sus jobs, así que nunca
prueba qué pasa cuando falta alguna, que es justo el caso de un entorno de
producción recién armado. Estos tests cargan settings.py en un proceso aparte,
con el entorno que cada caso necesita y sin leer el .env local, que en
desarrollo trae DEBUG=True.
"""
import json
import os
import subprocess
import sys
import textwrap

from django.conf import settings
from django.test import SimpleTestCase

CARGAR_SETTINGS = textwrap.dedent("""
    import json
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False  # no leer el .env local
    from gestionInstituto import settings
    print(json.dumps({
        'DEBUG': settings.DEBUG,
        'ENGINE': settings.DATABASES['default']['ENGINE'],
    }))
""")

# Lo mínimo que producción tiene que tener cargado (ver docs/PRODUCCION_VERCEL.md).
PRODUCCION = {
    'SECRET_KEY': 'clave-de-prueba-' + 'x' * 40,
    'ALLOWED_HOSTS': 'www.ejemplo.edu.ar',
    'DATABASE_URL': 'postgres://usuario:clave@localhost:5432/simef',
}


def cargar_settings(**variables):
    """Carga settings.py con solo estas variables (más PATH) y devuelve el proceso."""
    entorno = {'PATH': os.environ.get('PATH', '')}
    entorno.update({k: v for k, v in variables.items() if v is not None})
    return subprocess.run(
        [sys.executable, '-c', CARGAR_SETTINGS],
        cwd=settings.BASE_DIR, env=entorno, capture_output=True, text=True, timeout=60,
    )


def resultado(proceso):
    return json.loads(proceso.stdout.strip().splitlines()[-1])


class DebugPorDefectoTest(SimpleTestCase):

    def test_sin_la_variable_debug_queda_apagado(self):
        """Si esto falla, un deploy sin DEBUG cargado muestra código y configuración."""
        proceso = cargar_settings(**PRODUCCION)
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIs(resultado(proceso)['DEBUG'], False)

    def test_solo_true_exacto_lo_prende(self):
        for valor, esperado in [('True', True), ('true', False), ('1', False), ('False', False)]:
            with self.subTest(DEBUG=valor):
                proceso = cargar_settings(DEBUG=valor, **PRODUCCION)
                self.assertEqual(proceso.returncode, 0, proceso.stderr)
                self.assertIs(resultado(proceso)['DEBUG'], esperado)


class VariablesObligatoriasEnProduccionTest(SimpleTestCase):
    """Con DEBUG apagado, la app no arranca si falta una variable de producción."""

    def test_cada_variable_obligatoria_frena_el_arranque(self):
        for variable in PRODUCCION:
            with self.subTest(falta=variable):
                proceso = cargar_settings(**{**PRODUCCION, variable: None})
                self.assertNotEqual(proceso.returncode, 0)
                self.assertIn(f'Falta la variable de entorno {variable}', proceso.stderr)

    def test_con_todas_las_variables_usa_postgres(self):
        proceso = cargar_settings(**PRODUCCION)
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertEqual(resultado(proceso)['ENGINE'], 'django.db.backends.postgresql')

    def test_en_desarrollo_no_hace_falta_ninguna(self):
        """Con DEBUG=True arranca sin variables y usa el SQLite local."""
        proceso = cargar_settings(DEBUG='True')
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertEqual(resultado(proceso)['ENGINE'], 'django.db.backends.sqlite3')
