import django.core.validators
from django.db import migrations, models


def backfill_dni(apps, schema_editor):
    """
    Cuentas creadas antes de este cambio podían no tener DNI cargado (el
    campo era opcional). Antes de volverlo obligatorio hay que darles un
    valor único: se usa un placeholder claramente falso (900000000 + id)
    para que no choque con un DNI real y quede fácil de detectar y corregir
    a mano.
    """
    Usuario = apps.get_model('inscripcionFinales', 'Usuario')
    for usuario in Usuario.objects.filter(dni__isnull=True):
        usuario.dni = 900000000 + usuario.pk
        usuario.save(update_fields=['dni'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0020_bloqueo_login_progresivo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='email'),
        ),
        migrations.RunPython(backfill_dni, noop),
        migrations.AlterField(
            model_name='usuario',
            name='dni',
            field=models.CharField(
                max_length=15, unique=True, verbose_name='dni',
                validators=[django.core.validators.RegexValidator(r'^[0-9]+$', 'El DNI solo puede tener números.')],
            ),
        ),
    ]
