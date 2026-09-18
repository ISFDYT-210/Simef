# ══════════════════════════════════════════════════════════════════════════
# Corrige el bug de las tablas con selección/paginación de Alpine.
# Dentro de un método, this.$el es contextual (la fila o el botón que disparó
# la evaluación), NO el contenedor. Eso hacía que las filas se ocultaran y que
# la selección múltiple no funcionara. $root SIEMPRE apunta al contenedor raíz
# del componente, así que reemplazamos this.$el.querySelector -> this.$root...
#
# Uso (desde la raíz del proyecto):  python corregir_tablas_alpine.py
# Hace backup (.bak) de cada archivo tocado y es idempotente.
# ══════════════════════════════════════════════════════════════════════════
import os, shutil

BASE = 'inscripcionFinales/templates/'
OLD = 'this.$el.querySelector'      # cubre querySelector y querySelectorAll
NEW = 'this.$root.querySelector'

if not os.path.isdir(BASE):
    raise SystemExit("No encuentro %s. Ejecutalo desde la raíz del proyecto." % BASE)

cambiados = []
for root, _dirs, files in os.walk(BASE):
    for fn in files:
        if not fn.endswith('.html'):
            continue
        ruta = os.path.join(root, fn)
        contenido = open(ruta, encoding='utf-8').read()
        if OLD not in contenido:
            continue
        n = contenido.count(OLD)
        shutil.copy(ruta, ruta + '.bak')
        open(ruta, 'w', encoding='utf-8').write(contenido.replace(OLD, NEW))
        cambiados.append((ruta.replace(BASE, ''), n))

if not cambiados:
    print("No quedaba ninguna plantilla con el patrón (ya estaban corregidas).")
else:
    print("Plantillas corregidas:")
    for r, n in cambiados:
        print(f"  ✔ {r}  ({n} ocurrencia/s)")
    print(f"\nTotal: {len(cambiados)} archivo(s). Reiniciá el runserver y Ctrl+F5.")
