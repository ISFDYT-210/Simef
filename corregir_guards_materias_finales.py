# ══════════════════════════════════════════════════════════════════════════
# Corrige el control de acceso (guard interno) de las pantallas de materias y
# finales que hoy muestran el cartel "No deberías estar acá" a roles que SÍ
# deberían entrar (Director, Secretario, Preceptor, Profesor).
#
# Reemplaza el guard viejo (is_staff / is_superuser / admin) por la CAPACIDAD
# que corresponde a cada pantalla, según la matriz de roles.
#
# Uso (desde la raíz del proyecto):  python corregir_guards_materias_finales.py
# Hace backup (.bak) de cada archivo y es idempotente.
# ══════════════════════════════════════════════════════════════════════════
import re, shutil, os

BASE = 'inscripcionFinales/templates/'

# cada pantalla -> capacidad que debe exigir
MAPA = {
    'materias/lista_materias_admin.html':    'puede_ver_materias',      # Dir/Sec/Prec
    'materias/inscripcion_materia_adm.html': 'puede_administrar',       # Dir/Sec/Prec
    'materias/cargar_nota.html':             'puede_cargar_notas',      # Prec/Prof
    'materias/lista_acta_volante.html':      'puede_ver_reportes',      # Dir/Sec/Prec/Prof
    'finales/list_mesa.html':                'puede_gestionar_mesas',   # Dir/Sec/Prec
    'finales/list_inscripcion.html':         'puede_administrar',       # Dir/Sec/Prec
    'finales/delete_mesa.html':              'puede_gestionar_mesas',   # Dir/Sec/Prec
    'finales/delete_inscripcion.html':       'puede_administrar',       # Dir/Sec/Prec
    'finales/lista_acta_volante.html':       'puede_ver_reportes',      # Dir/Sec/Prec/Prof
}

PATRON = re.compile(
    r"\{%\s*if\s+request\.user\.is_staff\s+or\s+request\.user\.is_superuser\s+or\s+request\.user\.(?:is_admin|admin)\s*%\}"
)

total = 0
for rel, cap in MAPA.items():
    ruta = BASE + rel
    if not os.path.exists(ruta):
        print(f"  (no existe, salteo): {rel}"); continue
    contenido = open(ruta, encoding='utf-8').read()
    nuevo, n = PATRON.subn("{%% if request.user.%s %%}" % cap, contenido)
    if n == 0:
        ya = any("request.user.%s" % cap in contenido for cap in [cap])
        print(f"  {rel}: 0 cambios {'(ya corregido)' if ya else '(no encontré el guard — avisame)'}")
        continue
    shutil.copy(ruta, ruta + '.bak')
    open(ruta, 'w', encoding='utf-8').write(nuevo)
    total += n
    print(f"  ✔ {rel}: {n} → {cap}")

print(f"\nTotal corregido: {total}. Reiniciá el runserver y recargá con Ctrl+F5.")
