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
from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# El hasher por defecto es lento a propósito; en los tests no aporta nada.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
