#!/usr/bin/env bash
# Regenera el diagrama interactivo de arquitectura (docs/diagramas/arquitectura.html)
# a partir de docs/diagramas/arquitectura.architecture.json, con Archify
# (https://github.com/tt-a1i/archify). GitHub Pages lo publica en cada push a
# main (.github/workflows/pages.yml).
#
#   ARCHIFY=/ruta/a/archify ./scripts/diagrama_arquitectura.sh
#
# ARCHIFY es la carpeta de la skill (la que tiene bin/archify.mjs); por defecto
# .claude/skills/archify. El chequeo en navegador necesita Chrome o Chromium: si
# no está en el PATH, indicarlo con ARCHIFY_CHROME=/ruta/al/ejecutable.
#
# Cada componente del JSON cita las líneas de código que lo respaldan, fijadas a
# un commit (meta.repository.revision). Si cambia la arquitectura, actualizar las
# citas y el commit antes de regenerar.
set -euo pipefail

cd "$(dirname "$0")/.."
ARCHIFY="${ARCHIFY:-.claude/skills/archify}"
ENTRADA=docs/diagramas/arquitectura.architecture.json
SALIDA=docs/diagramas/arquitectura.html
EVIDENCIA="$(mktemp -d)"
trap 'rm -rf "$EVIDENCIA"' EXIT

ARCHIFY_UPDATE_CHECK_DISABLED=1 node "$ARCHIFY/bin/archify.mjs" finalize architecture \
  "$ENTRADA" "$SALIDA" --repo-root . --quality showcase --out-dir "$EVIDENCIA" --json > "$EVIDENCIA/resultado.json" || {
  cat "$EVIDENCIA/resultado.json"
  exit 1
}
# Los comprobantes de entrega quedan junto al HTML: no se versionan.
rm -f docs/diagramas/arquitectura.*.json.tmp docs/diagramas/arquitectura.deliver*.json \
  docs/diagramas/arquitectura.finalize*.json

# Archify 3.2 abre las páginas nuevas con la animación en pausa, y en pausa no se
# ve el recorrido de las flechas al pasar el cursor. Que arranque en movimiento
# salvo que el lector la haya pausado (y que la pausa quede guardada).
python3 - "$SALIDA" <<'EOF'
import sys
ruta = sys.argv[1]
html = open(ruta, encoding='utf-8').read()
cambios = [
    ("          if (readerPaused) localStorage.removeItem(STORAGE_KEY);\n"
     "          else localStorage.setItem(STORAGE_KEY, 'live');",
     "          localStorage.setItem(STORAGE_KEY, readerPaused ? 'still' : 'live');"),
    ("      readerPaused = readStored() !== 'live';",
     "      // SIMEF: arranca en Live (como Archify 3.0) salvo que el lector la haya pausado.\n"
     "      readerPaused = readStored() === 'still';"),
]
for viejo, nuevo in cambios:
    if html.count(viejo) != 1:
        sys.exit(f'No encontré exactamente una vez el código a ajustar en {ruta}: '
                 'cambió Archify, revisar el arranque de la animación.')
    html = html.replace(viejo, nuevo)
open(ruta, 'w', encoding='utf-8').write(html)
EOF
echo "Diagrama regenerado en $SALIDA"
