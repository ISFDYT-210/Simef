from django.db import migrations


# Mapeo de los códigos legacy (mezcla de MODALIDAD_CHOICES viejo '01'/'02'/'03'
# y los valores que quedaban truncados por el <int:modalidad> de la URL de
# autoinscripción, que perdía el cero adelante) a las palabras que ya usa toda
# la lógica de negocio.
MAPEO_LEGACY = {
    '01': 'Oyente',
    '02': 'Regular',
    '03': 'Itinerante',
    '1': 'Regular',   # '01' truncado por el path converter <int:modalidad>
    '2': 'Libre',     # '02' truncado; en la URL del alumno significaba "Libre"
}


def normalizar(apps, schema_editor):
    usuarios_materia = apps.get_model('inscripcionFinales', 'usuarios_materia')
    for valor_viejo, valor_nuevo in MAPEO_LEGACY.items():
        usuarios_materia.objects.filter(modalidad=valor_viejo).update(modalidad=valor_nuevo)


def revertir(apps, schema_editor):
    """No se revierte: no hay forma de distinguir '1' legacy de un nuevo registro sin código."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0010_estado_inicial_cursadas'),
    ]

    operations = [
        migrations.RunPython(normalizar, revertir),
    ]
