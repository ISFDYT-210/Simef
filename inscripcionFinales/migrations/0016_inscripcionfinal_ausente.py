"""
Agrega InscripcionFinal.ausente sin romper las bases donde la columna ya existe.

La columna la creó en Neon el 06/10 una migración (0009_inscripcionfinal_ausente)
que nunca llegó al repositorio. Como el modelo no tenía el campo, Django no
completaba la columna al insertar y toda inscripción a un final fallaba con
IntegrityError (#103, #119).

Por eso esta migración no usa un AddField común, que en Neon fallaría con
"column already exists":

1. Agrega el campo al estado de las migraciones, sin tocar la base.
2. Crea la columna solo si falta: en una base nueva (CI, instalaciones limpias)
   la crea; en Neon y en las copias locales de Neon no hace nada.

En las dos situaciones la columna termina igual: booleana, NOT NULL y sin valor
por defecto en la base. Django la completa con False en cada INSERT.

Si alguien todavía tiene el archivo 0009_inscripcionfinal_ausente.py en una rama
local, no hay que subirlo: agregaría el mismo campo por segunda vez.
"""
from django.db import migrations, models


def _columnas(schema_editor, tabla):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, tabla)}


def agregar_columna_si_falta(apps, schema_editor):
    InscripcionFinal = apps.get_model('inscripcionFinales', 'InscripcionFinal')
    if 'ausente' not in _columnas(schema_editor, InscripcionFinal._meta.db_table):
        schema_editor.add_field(InscripcionFinal, InscripcionFinal._meta.get_field('ausente'))


def quitar_columna(apps, schema_editor):
    # Revertir borra la columna y lo que tenga cargado, como un RemoveField.
    InscripcionFinal = apps.get_model('inscripcionFinales', 'InscripcionFinal')
    if 'ausente' in _columnas(schema_editor, InscripcionFinal._meta.db_table):
        schema_editor.remove_field(InscripcionFinal, InscripcionFinal._meta.get_field('ausente'))


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0015_alter_usuario_telefono_1_alter_usuario_telefono_2'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='inscripcionfinal',
                    name='ausente',
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
        migrations.RunPython(agregar_columna_si_falta, quitar_columna),
    ]
