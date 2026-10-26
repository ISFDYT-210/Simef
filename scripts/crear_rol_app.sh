#!/usr/bin/env bash
# Crea (o renueva la contraseña de) el usuario de base con el que se conecta la
# app en Vercel: puede leer y escribir datos, pero no crear, modificar ni borrar
# tablas (SEC-05, MOP OP-12). Las migraciones siguen corriendo con el dueño de
# la base, desde scripts/migrar_neon.sh.
#
# Uso: ./scripts/crear_rol_app.sh preview|produccion
#
# Lee la cadena del dueño desde el .env (PREVIEW_DATABASE_URL o DATABASE_URL)
# sin mostrarla. Genera una contraseña nueva y guarda la cadena del usuario de
# la app en el .env (PREVIEW_APP_DATABASE_URL o APP_DATABASE_URL), para copiarla
# a la variable DATABASE_URL del entorno que corresponda en Vercel. No imprime
# ninguna contraseña.
set -euo pipefail

ROL_APP=simef_app

case "${1:-}" in
  preview)    VAR_DUENO=PREVIEW_DATABASE_URL; VAR_APP=PREVIEW_APP_DATABASE_URL ;;
  produccion) VAR_DUENO=DATABASE_URL;         VAR_APP=APP_DATABASE_URL ;;
  *) echo "Uso: $0 preview|produccion" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/.."
[ -f .env ] || { echo "ERROR: falta el .env" >&2; exit 1; }
docker image inspect simef-web >/dev/null 2>&1 || {
  echo "ERROR: falta la imagen simef-web. Correr antes: docker compose build web" >&2; exit 1; }

# Lee las cadenas del .env sin mostrarlas y controla que sean de Neon y que la
# de preview no sea la de producción.
SALIDA=$(python3 - "$VAR_DUENO" <<'EOF'
import sys
from urllib.parse import urlsplit
valores = {}
for linea in open('.env', encoding='utf-8'):
    linea = linea.strip()
    if linea and not linea.startswith('#') and '=' in linea:
        clave, valor = linea.split('=', 1)
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
var = sys.argv[1]
url = valores.get(var, '')
if not url:
    sys.exit(f'ERROR: falta {var} en el .env')
host = urlsplit(url).hostname or ''
if not host.endswith('.neon.tech'):
    sys.exit(f'ERROR: {var} no apunta a Neon')
endpoint = host.split('.')[0].removesuffix('-pooler')
if var == 'PREVIEW_DATABASE_URL':
    prod = urlsplit(valores.get('DATABASE_URL', '')).hostname or ''
    if prod.split('.')[0].removesuffix('-pooler') == endpoint:
        sys.exit('ERROR: PREVIEW_DATABASE_URL apunta a la base de producción')
print(f'ENDPOINT={endpoint}')
EOF
) || exit 1
eval "$SALIDA"

echo "==> Destino: $1 (endpoint de Neon: $ENDPOINT)"
if [ "$1" = produccion ]; then
  read -r -p "Para confirmar, escribí el destino ('produccion'): " RESP
  [ "$RESP" = produccion ] || { echo "Cancelado." >&2; exit 1; }
fi

DATABASE_URL=$(python3 -c "
for l in open('.env', encoding='utf-8'):
    l = l.strip()
    if l.startswith('$VAR_DUENO='):
        print(l.split('=', 1)[1].strip().strip('\"').strip(\"'\")); break
")
APP_PASSWORD=$(python3 -c "import secrets, string; a = string.ascii_letters + string.digits; print(''.join(secrets.choice(a) for _ in range(40)))")
export DATABASE_URL APP_PASSWORD

# Crea el usuario, le da permisos solo sobre los datos y los deja como permisos
# por defecto para las tablas que creen las migraciones futuras. Después se
# conecta como ese usuario y comprueba que lee pero no puede crear tablas.
APP_URL=$(docker run --rm -i -e DATABASE_URL -e APP_PASSWORD -e ROL_APP="$ROL_APP" \
  --entrypoint python simef-web - <<'EOF'
import os
import sys
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg2
from psycopg2 import errors, sql

rol = os.environ['ROL_APP']
password = os.environ['APP_PASSWORD']
url = os.environ['DATABASE_URL']

conn = psycopg2.connect(url)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute('select current_user, current_database()')
    dueno, base = cur.fetchone()
    cur.execute('select 1 from pg_roles where rolname = %s', [rol])
    existe = cur.fetchone()
    accion = 'ALTER' if existe else 'CREATE'
    cur.execute(sql.SQL(accion + ' ROLE {} WITH LOGIN PASSWORD {}').format(
        sql.Identifier(rol), sql.Literal(password)))
    for sentencia in [
        'GRANT CONNECT ON DATABASE {base} TO {rol}',
        'GRANT USAGE ON SCHEMA public TO {rol}',
        'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {rol}',
        'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {rol}',
        'ALTER DEFAULT PRIVILEGES FOR ROLE {dueno} IN SCHEMA public '
        'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {rol}',
        'ALTER DEFAULT PRIVILEGES FOR ROLE {dueno} IN SCHEMA public '
        'GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {rol}',
    ]:
        cur.execute(sql.SQL(sentencia).format(
            base=sql.Identifier(base), rol=sql.Identifier(rol), dueno=sql.Identifier(dueno)))
    print(f'    {"Usuario renovado" if existe else "Usuario creado"}: {rol}', file=sys.stderr)

partes = urlsplit(url)
netloc = f'{quote(rol)}:{quote(password)}@{partes.hostname}' + (f':{partes.port}' if partes.port else '')
app_url = urlunsplit((partes.scheme, netloc, partes.path, partes.query, partes.fragment))

conn.close()

conn = psycopg2.connect(app_url)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute('select count(*) from "inscripcionFinales_usuario"')
    usuarios = cur.fetchone()[0]
    print(f'    Como {rol}: lee la tabla de usuarios ({usuarios} filas)', file=sys.stderr)
    try:
        cur.execute('create table prueba_permisos_simef (id int)')
        cur.execute('drop table prueba_permisos_simef')
        sys.exit(f'ERROR: {rol} pudo crear una tabla; revisar los permisos del esquema public')
    except errors.InsufficientPrivilege:
        print(f'    Como {rol}: no puede crear tablas (correcto)', file=sys.stderr)

conn.close()
print(app_url)
EOF
) || exit 1

# Guarda la cadena del usuario de la app en el .env, reemplazando la anterior.
APP_URL="$APP_URL" python3 - "$VAR_APP" <<'EOF'
import os
import sys
var = sys.argv[1]
lineas = [l for l in open('.env', encoding='utf-8').read().splitlines() if not l.startswith(var + '=')]
lineas.append(f"{var}={os.environ['APP_URL']}")
open('.env', 'w', encoding='utf-8').write('\n'.join(lineas) + '\n')
EOF

echo "==> Listo. La cadena quedó en el .env como $VAR_APP (no se muestra)."
if [ "$1" = produccion ]; then
  echo "    NO la cargues todavía en Vercel si producción tiene migraciones pendientes:"
  echo "    primero ./scripts/migrar_neon.sh produccion, y recién después ponerla en"
  echo "    DATABASE_URL de Production, como Sensitive, y redeployar (MOP OP-01 y OP-12)."
else
  echo "    Copiarla en Vercel a la variable DATABASE_URL del entorno Preview, como"
  echo "    Sensitive, y volver a desplegar."
fi
echo "    Las migraciones siguen usando $VAR_DUENO (el dueño)."
