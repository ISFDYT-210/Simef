# Baja lógica en vez de borrado (#270).
#
# 1. Materias, mesas de final e inscripciones a final tienen `activo`: darlas de
#    baja ya no borra nada. La columna queda con DEFAULT true en la base, así la
#    versión anterior de la app puede seguir dando de alta filas mientras se
#    publica esta (y si hubiera que volver atrás).
# 2. Las relaciones que llevan a cursadas, notas, inscripciones o actas pasan de
#    CASCADE a PROTECT. Es un cambio solo de Django: en la base no cambia nada
#    (sqlmigrate da "no-op"), porque las claves foráneas ya rechazaban borrar
#    una fila con dependientes; el borrado en cascada lo hacía Django.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0024_auditoria_estructurada_inmodificable'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcionfinal',
            name='activo',
            field=models.BooleanField(db_default=True, default=True, verbose_name='De alta'),
        ),
        migrations.AddField(
            model_name='materia',
            name='activo',
            field=models.BooleanField(db_default=True, default=True, verbose_name='De alta'),
        ),
        migrations.AddField(
            model_name='mesafinal',
            name='activo',
            field=models.BooleanField(db_default=True, default=True, verbose_name='De alta'),
        ),
        migrations.AlterField(
            model_name='carrera',
            name='instituto',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='inscripcionFinales.instituto'),
        ),
        migrations.AlterField(
            model_name='inscripcionfinal',
            name='llamado',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inscripcionFinales.mesafinal'),
        ),
        migrations.AlterField(
            model_name='inscripcionfinal',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='materia',
            name='carrera',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='inscripcionFinales.carrera'),
        ),
        migrations.AlterField(
            model_name='materia',
            name='profesor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='mesafinal',
            name='materia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inscripcionFinales.materia'),
        ),
        migrations.AlterField(
            model_name='tribunalmesa',
            name='docente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tribunales', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='usuarios_materia',
            name='materia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inscripcionFinales.materia'),
        ),
        migrations.AlterField(
            model_name='usuarios_materia',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
    ]
