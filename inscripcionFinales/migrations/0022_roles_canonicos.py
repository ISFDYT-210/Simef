from django.db import migrations

ROLES = ['Directivo', 'Secretario', 'Preceptor', 'Profesor', 'Estudiante']


def normalizar_roles(apps, schema_editor):
    """
    Lleva cada rol a la forma exacta de Usuario.ROL_CHOICES. Había cuentas
    con el rol escrito de otra manera (por ejemplo 'PRECEPTOR'), que no
    coincide con CAPACIDADES_POR_ROL y deja a la cuenta sin permisos.
    Un valor que no corresponde a ningún rol se deja como está.
    """
    Usuario = apps.get_model('inscripcionFinales', 'Usuario')
    for rol in ROLES:
        Usuario.objects.filter(rol__iexact=rol).exclude(rol=rol).update(rol=rol)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0021_login_por_dni'),
    ]

    operations = [
        migrations.RunPython(normalizar_roles, noop),
    ]
