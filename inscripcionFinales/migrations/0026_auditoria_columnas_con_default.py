# Las columnas que la 0024 (#271) agregó a la auditoría quedan con DEFAULT '' en la
# base. Sin eso, mientras se publica esta versión (la migración corre antes que el
# código nuevo) o si hubiera que volver a la 1.0.0, la versión anterior falla en
# cada acción que registra auditoría: no conoce esas columnas y son NOT NULL.
# Solo cambia el valor por defecto de las columnas: no toca filas, así que el
# trigger de la 0024 no interviene.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0025_baja_logica_y_protect'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroauditoria',
            name='autor_dni',
            field=models.CharField(blank=True, db_default='', default='', max_length=20, verbose_name='DNI del autor'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='autor_nombre',
            field=models.CharField(blank=True, db_default='', default='', max_length=255, verbose_name='Autor'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='autor_rol',
            field=models.CharField(blank=True, db_default='', default='', max_length=20, verbose_name='Rol del autor'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='motivo',
            field=models.TextField(blank=True, db_default='', default='', verbose_name='Motivo'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='valor_anterior',
            field=models.TextField(blank=True, db_default='', default='', verbose_name='Valor anterior'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='valor_nuevo',
            field=models.TextField(blank=True, db_default='', default='', verbose_name='Valor nuevo'),
        ),
    ]
