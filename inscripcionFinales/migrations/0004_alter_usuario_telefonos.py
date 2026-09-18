from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0003_registroauditoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='telefono_1',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='telefono_1'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='telefono_2',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='telefono_2'),
        ),
    ]
