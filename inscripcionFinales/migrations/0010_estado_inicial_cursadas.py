from django.db import migrations


def asignar_estado_inicial(apps, schema_editor):
    """
    Los registros existentes solo tenían nota_cursada/nota_final: se les
    asigna un `estado` inicial coherente con esos datos.
    - final >= 4            -> APROBADO
    - cursada >= 4 (sin final aprobado) -> REGULAR
    - cursada < 4            -> RECURSA
    - sin ninguna nota       -> se deja EN_CURSO (valor por defecto)
    """
    usuarios_materia = apps.get_model('inscripcionFinales', 'usuarios_materia')

    usuarios_materia.objects.filter(nota_final__gte=4).update(estado='APROBADO')
    usuarios_materia.objects.filter(
        nota_final__isnull=True, nota_cursada__gte=4
    ).update(estado='REGULAR')
    usuarios_materia.objects.filter(
        nota_final__isnull=True, nota_cursada__lt=4
    ).update(estado='RECURSA')


def revertir(apps, schema_editor):
    """No hay información suficiente para reconstruir el estado previo (no existía)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0009_usuarios_materia_estado_and_more'),
    ]

    operations = [
        migrations.RunPython(asignar_estado_inicial, revertir),
    ]
