# ══════════════════════════════════════════════════════════════════════════
# Agrega @capacidad_requerida a las vistas que quedaron sin control de acceso.
# Uso:  desde la raíz del proyecto (donde está manage.py):
#           python aplicar_permisos_vistas.py
# Hace un backup (views.py.bak) y es idempotente (si ya tiene decorador, salta).
# ══════════════════════════════════════════════════════════════════════════
import shutil, os, ast

RUTA = 'inscripcionFinales/views.py'

# vista -> decorador (capacidad mínima según la matriz de roles)
MAPA = {
    'altaMesa':                      "@capacidad_requerida('gestionar_mesas')",
    'editMesa':                      "@capacidad_requerida('gestionar_mesas')",
    'inscripcionMateria':            "@capacidad_requerida('abrir_inscripciones')",
    'inscripcionMateriaEst':         "@capacidad_requerida('inscribirse')",
    'inscripcionFinalEst':           "@capacidad_requerida('inscribirse')",
    'lista_materias_inscriptas_adm': "@capacidad_requerida('ver_reportes', 'cargar_notas')",
    'inscribir_mesa_final':          "@capacidad_requerida('abrir_inscripciones')",
    'inscripcionMesa':               "@capacidad_requerida('abrir_inscripciones')",
    'listar_usuarios_materia':       "@capacidad_requerida('ver_materias')",
}

if not os.path.exists(RUTA):
    raise SystemExit("No encuentro %s. Ejecutalo desde la raíz del proyecto." % RUTA)

lines = open(RUTA, encoding='utf-8').read().split('\n')
out, agregados, saltados = [], [], []
for line in lines:
    for nombre, deco in MAPA.items():
        if line.startswith('def %s(' % nombre):
            prev = out[-1].strip() if out else ''
            if prev.startswith('@'):
                saltados.append(nombre)
            else:
                out.append(deco)
                agregados.append(nombre)
            break
    out.append(line)

nuevo = '\n'.join(out)
# validar que sigue siendo Python válido antes de escribir
ast.parse(nuevo)

shutil.copy(RUTA, RUTA + '.bak')
open(RUTA, 'w', encoding='utf-8').write(nuevo)

print("Backup guardado en:", RUTA + '.bak')
print("Decoradores agregados (%d): %s" % (len(agregados), ', '.join(agregados) or '—'))
print("Ya protegidas, salteadas (%d): %s" % (len(saltados), ', '.join(saltados) or '—'))
print("Listo. Reiniciá el runserver.")
