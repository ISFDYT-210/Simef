"""
Settings para correr los tests.

Hereda todo de settings.py (apps instaladas, middleware, usuario custom) y solo
reemplaza la base de datos: los tests corren sobre SQLite en memoria para no
tocar la Postgres compartida de Neon, que es la que settings.py toma del
DATABASE_URL del .env. Sin esto, `manage.py test` intentaría crear una base
`test_neondb` en el Neon del equipo.

Uso:

    python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
"""
import os

# Los tests no necesitan las variables obligatorias de producción (SECRET_KEY,
# ALLOWED_HOSTS, DATABASE_URL): sin un .env, settings.py arranca en modo
# desarrollo. El test runner de Django apaga DEBUG igual al correr.
os.environ.setdefault('DEBUG', 'True')

from .settings import *  # noqa: F401,F403,E402

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# El cliente de pruebas pide por http: si se corren los tests con DEBUG=False,
# la redirección a HTTPS convertiría cada respuesta en un 301.
SECURE_SSL_REDIRECT = False

# El hasher por defecto es lento a propósito; en los tests no aporta nada.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
