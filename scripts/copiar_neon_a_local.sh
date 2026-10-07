#!/usr/bin/env bash
#
# Copia la base de Neon a la Postgres local del docker-compose, para poder
# probar contra datos reales sin tocar la base del instituto.
#
#   ./scripts/copiar_neon_a_local.sh                 # baja un dump nuevo y lo restaura
#   ./scripts/copiar_neon_a_local.sh backups/x.sql   # restaura un dump que ya tenes
#
# A Neon se lo LEE y nada mas: pg_dump no escribe. Lo que se borra y se recrea
# es la base LOCAL. El script se niega a hacerlo si el destino no es local.
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "ERROR: falta .env en la raiz del repo" >&2; exit 1; }

# Las credenciales salen del .env con Python, no con grep: la contraseña puede
# traer caracteres que rompen el parseo a mano o el de la URI de psql.
eval "$(python3 - <<'PY'
import os
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
load_dotenv('.env')
url = os.environ.get('DATABASE_URL', '')
if not url:
    raise SystemExit("echo 'ERROR: DATABASE_URL no esta definido en .env' >&2; exit 1")
u = urlparse(url)
def q(s): return "'" + str(s).replace("'", "'\\''") + "'"
print(f"ORIGEN_HOST={q(u.hostname)}")
print(f"ORIGEN_PORT={q(u.port or 5432)}")
print(f"ORIGEN_DB={q(u.path.lstrip('/'))}")
print(f"ORIGEN_USER={q(unquote(u.username or ''))}")
print(f"ORIGEN_PASS={q(unquote(u.password or ''))}")
print(f"LOCAL_DB={q(os.environ['POSTGRES_DB'])}")
print(f"LOCAL_USER={q(os.environ['POSTGRES_USER'])}")
print(f"LOCAL_PASS={q(os.environ['POSTGRES_PASSWORD'])}")
PY
)"

SERVICIO_DB=$(docker compose ps -q db)
[ -n "$SERVICIO_DB" ] || { echo "ERROR: el contenedor 'db' no esta corriendo. Corre: docker compose up -d db" >&2; exit 1; }

# Guarda real: antes de borrar nada, preguntarle al servidor de DESTINO donde
# esta. Las ordenes de abajo entran por `docker exec` sin -h, asi que pegan al
# socket del contenedor; esto lo verifica en vez de darlo por sentado.
DESTINO_ADDR=$(docker exec -i -e PGPASSWORD="$LOCAL_PASS" "$SERVICIO_DB" \
  psql -U "$LOCAL_USER" -d postgres -tAc \
  "SELECT coalesce(host(inet_server_addr()), 'socket-local');" 2>/dev/null | tr -d '[:space:]')

case "$DESTINO_ADDR" in
  socket-local|127.0.0.1|::1|10.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*|192.168.*)
    echo "==> Destino verificado: $DESTINO_ADDR (dentro del contenedor)" ;;
  "")
    echo "ERROR: no se pudo verificar donde esta el servidor de destino. Abortando." >&2; exit 1 ;;
  *)
    echo "ERROR: el destino ($DESTINO_ADDR) no es local. Me niego a borrar esa base." >&2; exit 1 ;;
esac

DUMP=${1:-}
if [ -z "$DUMP" ]; then
  mkdir -p backups
  DUMP="backups/neon-$(date +%Y-%m-%d-%H%M).sql"
  echo "==> Bajando dump de ${ORIGEN_HOST} (solo lectura)"
  # pg_dump corre DENTRO del contenedor: ahi esta la version 16 del cliente,
  # asi no hace falta instalar postgresql-client en la maquina.
  docker exec -i \
    -e PGPASSWORD="$ORIGEN_PASS" -e PGSSLMODE=require \
    "$SERVICIO_DB" \
    pg_dump -h "$ORIGEN_HOST" -p "$ORIGEN_PORT" -U "$ORIGEN_USER" -d "$ORIGEN_DB" \
            --no-owner --no-privileges --clean --if-exists \
    > "$DUMP"
  echo "    $DUMP  ($(du -h "$DUMP" | cut -f1))"
else
  [ -f "$DUMP" ] || { echo "ERROR: no existe $DUMP" >&2; exit 1; }
  echo "==> Usando el dump existente: $DUMP"
fi

echo "==> Recreando la base local '${LOCAL_DB}'"
# La app mantiene conexiones abiertas; sin cerrarlas, el DROP DATABASE falla.
docker exec -i -e PGPASSWORD="$LOCAL_PASS" "$SERVICIO_DB" \
  psql -U "$LOCAL_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
 WHERE datname = '${LOCAL_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${LOCAL_DB}";
CREATE DATABASE "${LOCAL_DB}" OWNER "${LOCAL_USER}";
SQL

echo "==> Restaurando"
docker exec -i -e PGPASSWORD="$LOCAL_PASS" "$SERVICIO_DB" \
  psql -U "$LOCAL_USER" -d "$LOCAL_DB" -q -v ON_ERROR_STOP=1 > /dev/null < "$DUMP"

echo "==> Listo. Contenido de la copia local:"
docker exec -i -e PGPASSWORD="$LOCAL_PASS" "$SERVICIO_DB" \
  psql -U "$LOCAL_USER" -d "$LOCAL_DB" -tAc "
    SELECT '    usuarios:  ' || (SELECT count(*) FROM \"inscripcionFinales_usuario\")
        || E'\n    materias:  ' || (SELECT count(*) FROM \"inscripcionFinales_materia\")
        || E'\n    mesas:     ' || (SELECT count(*) FROM \"inscripcionFinales_mesafinal\")
        || E'\n    migracion: ' || (SELECT max(name) FROM django_migrations WHERE app='inscripcionFinales');"

echo
echo "La app ya apunta aca: docker-compose.override.yml define DATABASE_URL hacia 'db'."
echo "Reinicia el contenedor web para que la tome:  docker compose restart web"
