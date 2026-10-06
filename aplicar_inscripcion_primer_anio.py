# ══════════════════════════════════════════════════════════════════════════
# Agrega al final de inscripcionFinales/models.py un signal que inscribe
# automáticamente a cada ESTUDIANTE en todas las materias de PRIMER AÑO de la
# carrera que se le asigna (cursada en bloque). Cubre todos los flujos de
# registro porque escucha el M2M Usuario.carrera.
#
# Uso (desde la raíz del proyecto, donde está manage.py):
#     python aplicar_inscripcion_primer_anio.py
# Hace backup (models.py.bak) y es idempotente.
# ══════════════════════════════════════════════════════════════════════════
import shutil, os, ast

RUTA = 'inscripcionFinales/models.py'
MARCA = 'def inscribir_en_primer_anio('

BLOQUE = '''

# ══════════════════════════════════════════════════════════════════════════
# Inscripción automática a PRIMER AÑO (cursada en bloque).
# Al asignarle una carrera a un ESTUDIANTE, se lo inscribe en todas las
# materias de primer año de esa carrera. Escucha el M2M Usuario.carrera, así
# que cubre todos los flujos (alta individual, carga masiva, admin, etc.).
# ══════════════════════════════════════════════════════════════════════════
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=Usuario.carrera.through)
def inscribir_en_primer_anio(sender, instance, action, pk_set, **kwargs):
    if action != "post_add":
        return
    if not instance.es_estudiante():
        return
    for carrera_id in (pk_set or []):
        for materia in Materia.objects.filter(carrera_id=carrera_id, anio=1):
            usuarios_materia.objects.get_or_create(usuario=instance, materia=materia)
'''

if not os.path.exists(RUTA):
    raise SystemExit("No encuentro %s. Ejecutalo desde la raíz del proyecto." % RUTA)

contenido = open(RUTA, encoding='utf-8').read()
if MARCA in contenido:
    print("Ya estaba aplicado (encontré inscribir_en_primer_anio). No hago nada.")
    raise SystemExit(0)

nuevo = contenido.rstrip() + '\n' + BLOQUE
ast.parse(nuevo)  # validar sintaxis antes de escribir
shutil.copy(RUTA, RUTA + '.bak')
open(RUTA, 'w', encoding='utf-8').write(nuevo)
print("Backup:", RUTA + '.bak')
print("✔ Signal de inscripción a primer año agregado al final de models.py")
print("Reiniciá el runserver.")
