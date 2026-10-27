#!/usr/bin/env bash
#
# Aplica las migraciones de Django en una base de Neon, con controles para no
# migrar la base equivocada. Es el procedimiento OP-03 del MOP (docs/MOP.md).
#
#   ./scripts/migrar_neon.sh preview      # rama "preview" (PREVIEW_DATABASE_URL del .env)
#   ./scripts/migrar_neon.sh produccion   # base del instituto (DATABASE_URL del .env)
#
# Qué hace, en orden:
#   1. Lee la cadena de conexión del .env, sin mostrarla nunca.
#   2. Verifica que sea de Neon y, para "preview", que NO sea la de producción.
#   3. Muestra el plan (migrate --plan): no escribe nada.
#   4. Si hay migraciones pendientes, pide confirmación escrita; en producción,
#      además, que exista una rama de respaldo creada en Neon.
#   5. Aplica y vuelve a mostrar el plan, que tiene que quedar vacío.
#
# Corre Django dentro de la imagen de desarrollo (simef-web), con el código
# del repo montado de solo lectura y sin entrypoint.sh: entrypoint.sh migra al
# arrancar y lo haría contra la base que tenga a mano.
set -euo pipefail
cd "$(dirname "$0")/.."

DESTINO="${1:-}"
case "$DESTINO" in
  preview)    VARIABLE=PREVIEW_DATABASE_URL ;;
  produccion) VARIABLE=DATABASE_URL ;;
  *) echo "Uso: $0 preview|produccion" >&2; exit 2 ;;
esac

[ -f .env ] || { echo "ERROR: falta .env en la raiz del repo" >&2; exit 1; }
docker image inspect simef-web >/dev/null 2>&1 || {
  echo "ERROR: falta la imagen simef-web. Correr antes: docker compose build web" >&2; exit 1; }

# Mismo parseo que copiar_neon_a_local.sh: solo biblioteca estándar. La salida
# se captura primero: si Python falla o rechaza la cadena, el script corta acá
# (un `eval "$(...)"` directo seguiría de largo aunque fallara).
SALIDA=$(VARIABLE="$VARIABLE" DESTINO="$DESTINO" python3 - <<'PYENV'
import os
import sys
from urllib.parse import urlparse

env = {}
with open('.env', encoding='utf-8') as fh:
    for linea in fh:
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, _, valor = linea.partition('=')
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ('"', "'"):
            valor = valor[1:-1]
        env[clave.strip()] = valor

def falla(mensaje):
    print('ERROR: ' + mensaje, file=sys.stderr)
    sys.exit(1)

def q(s):
    return "'" + str(s).replace("'", "'\\''") + "'"

def endpoint(url):
    host = urlparse(url).hostname or ''
    return host.split('.')[0].replace('-pooler', '')

variable, destino = os.environ['VARIABLE'], os.environ['DESTINO']
url = env.get(variable, '')
if not url:
    falla(f'falta {variable} en el .env')
host = urlparse(url).hostname or ''
if not host.endswith('.neon.tech'):
    falla(f'{variable} no apunta a Neon (host: {host or "vacío"}). Me detengo.')
if destino == 'preview':
    prod = env.get('DATABASE_URL', '')
    if prod and endpoint(prod) == endpoint(url):
        falla('PREVIEW_DATABASE_URL es la MISMA base que producción. En Neon: Connect, '
              'elegir la rama preview en el selector Branch y copiar esa cadena.')
print(f"export DATABASE_URL={q(url)}")
print(f"ENDPOINT={q(endpoint(url))}")
PYENV
) || exit 1
eval "$SALIDA"

correr() {
  docker run --rm -v "$PWD":/app:ro -w /app -e PYTHONDONTWRITEBYTECODE=1 \
    -e DEBUG=True -e DATABASE_URL --entrypoint python simef-web manage.py "$@"
}

echo "==> Destino: $DESTINO (endpoint de Neon: $ENDPOINT)"
echo "==> Esquema de la base contra el código (no escribe nada):"
ESQUEMA=$(correr verificar_esquema 2>&1) || {
  echo "$ESQUEMA" | sed 's/^/    /'
  echo "ERROR: la base tiene cambios que el repo no conoce. No se migra hasta aclararlo (MOP OP-03)." >&2
  exit 1
}
echo "$ESQUEMA" | sed 's/^/    /'
echo "==> Plan (no escribe nada):"
PLAN=$(correr migrate --plan 2>&1) || {
  echo "$PLAN" | tail -3 | sed 's/^/    /'
  echo "ERROR: no se pudo leer el plan (¿conexión con Neon? ¿la rama existe?). No se escribió nada." >&2
  exit 1
}
echo "$PLAN" | sed 's/^/    /'
if echo "$PLAN" | grep -q "No planned migration operations"; then
  echo "==> No hay migraciones pendientes. Nada que hacer."
  exit 0
fi

if [ "$DESTINO" = produccion ]; then
  echo
  echo "Esto escribe en la base del INSTITUTO. Antes, en Neon: Branches > New branch"
  echo "desde la rama principal, con los datos actuales, llamada respaldo-AAAAMMDD."
  read -r -p "¿Ya existe la rama de respaldo de hoy? Escribí 'si': " RESP
  [ "$RESP" = si ] || { echo "Cancelado: primero la rama de respaldo." >&2; exit 1; }
  read -r -p "Para confirmar, escribí el destino ('produccion'): " RESP
  [ "$RESP" = produccion ] || { echo "Cancelado." >&2; exit 1; }
else
  read -r -p "¿Aplicar estas migraciones en la rama preview? Escribí 'aplicar': " RESP
  [ "$RESP" = aplicar ] || { echo "Cancelado." >&2; exit 1; }
fi

echo "==> Aplicando:"
correr migrate --noinput 2>&1 | sed 's/^/    /'
echo "==> Plan después (tiene que estar vacío):"
correr migrate --plan 2>&1 | tail -1 | sed 's/^/    /'
echo "==> Esquema después (tiene que coincidir, sin pendientes):"
ESQUEMA=$(correr verificar_esquema --sin-pendientes 2>&1) || {
  echo "$ESQUEMA" | sed 's/^/    /'
  echo "ERROR: después de migrar, el esquema no coincide con el código. Revisar antes de publicar." >&2
  exit 1
}
echo "$ESQUEMA" | sed 's/^/    /'
