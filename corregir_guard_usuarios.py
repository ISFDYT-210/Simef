# ══════════════════════════════════════════════════════════════════════════
# Corrige el control de acceso en las pantallas de gestión de usuarios.
# Reemplaza el guard viejo (is_staff / is_superuser / admin) por la capacidad
# puede_gestionar_usuarios, para que Director y Secretario vean el contenido
# (hoy el Director cae en el cartel de "No deberías estar acá").
#
# Uso (desde la raíz del proyecto, donde está manage.py):
#     python corregir_guard_usuarios.py
# Hace backup (.bak) de cada archivo y es idempotente.
# ══════════════════════════════════════════════════════════════════════════
import re, shutil, os

ARCHIVOS = [
    'inscripcionFinales/templates/registration/list_user.html',
    'inscripcionFinales/templates/registration/register.html',
]

# matchea el guard con cualquiera de las dos variantes (.admin o .is_admin)
PATRON = re.compile(
    r"\{%\s*if\s+request\.user\.is_staff\s+or\s+request\.user\.is_superuser\s+or\s+request\.user\.(?:is_admin|admin)\s*%\}"
)
NUEVO = "{% if request.user.puede_gestionar_usuarios %}"

total = 0
for ruta in ARCHIVOS:
    if not os.path.exists(ruta):
        print("  (no existe, salteo):", ruta); continue
    contenido = open(ruta, encoding='utf-8').read()
    nuevo, n = PATRON.subn(NUEVO, contenido)
    if n == 0:
        ya = "puede_gestionar_usuarios" in contenido
        print(f"  {ruta}: 0 cambios {'(ya estaba corregido)' if ya else '(no encontré el guard — avisame)'}")
        continue
    shutil.copy(ruta, ruta + '.bak')
    open(ruta, 'w', encoding='utf-8').write(nuevo)
    total += n
    print(f"  ✔ {ruta}: {n} guard(s) corregido(s)  (backup {ruta}.bak)")

print(f"\nTotal corregido: {total}. Reiniciá el runserver y recargá con Ctrl+F5.")
