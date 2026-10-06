#!/bin/sh
set -e

# Dejar a la vista contra que base se va a migrar, con la contraseña tapada.
# Esto no es decorativo: `migrate` corre en cada arranque del contenedor, y con
# un DATABASE_URL de produccion en el .env se le aplican a la base del instituto
# las migraciones de la rama en la que estes parado, sin que nada lo avise.
echo "==> base de datos: $(printf '%s' "${DATABASE_URL:-SQLite local (DATABASE_URL sin definir)}" | sed -E 's#://[^:]+:[^@]*@#://***:***@#')"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
