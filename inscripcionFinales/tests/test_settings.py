"""
Tests de la configuración de seguridad de settings.py (CICD-01, CICD-07).

El CI fija DEBUG='False' en todos sus jobs, así que nunca prueba qué pasa cuando
la variable falta, que es justo el caso de un entorno de producción recién
armado. Estos tests cargan settings.py en un proceso aparte, con el entorno que
cada caso necesita y sin leer el .env local, que en desarrollo trae DEBUG=True.
"""
import os
import subprocess
import sys
import textwrap

from django.conf import settings
from django.test import SimpleTestCase

CARGAR_SETTINGS = textwrap.dedent("""
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False  # no leer el .env local
    from gestionInstituto import settings
    print(settings.DEBUG)
""")


def cargar_settings(**variables):
    """Carga settings.py con solo estas variables (más PATH) y devuelve el proceso."""
    entorno = {'PATH': os.environ.get('PATH', '')}
    entorno.update(variables)
    return subprocess.run(
        [sys.executable, '-c', CARGAR_SETTINGS],
        cwd=settings.BASE_DIR, env=entorno, capture_output=True, text=True, timeout=60,
    )


class DebugPorDefectoTest(SimpleTestCase):

    def test_sin_la_variable_debug_queda_apagado(self):
        """Si esto falla, un deploy sin DEBUG cargado muestra código y configuración."""
        proceso = cargar_settings(SECRET_KEY='clave-de-prueba-' + 'x' * 40)
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertEqual(proceso.stdout.strip(), 'False')

    def test_solo_true_exacto_lo_prende(self):
        for valor, esperado in [('True', 'True'), ('true', 'False'), ('1', 'False'), ('False', 'False')]:
            with self.subTest(DEBUG=valor):
                proceso = cargar_settings(DEBUG=valor, SECRET_KEY='clave-de-prueba-' + 'x' * 40)
                self.assertEqual(proceso.returncode, 0, proceso.stderr)
                self.assertEqual(proceso.stdout.strip(), esperado)

    def test_sin_debug_ni_secret_key_no_arranca(self):
        proceso = cargar_settings()
        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn('Falta la variable de entorno SECRET_KEY', proceso.stderr)
