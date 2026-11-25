# Auditoría estructurada e inmodificable (#271).
#
# 1. Campos nuevos: el autor copiado al registro (DNI, nombre y rol, para que
#    no se pierda si se borra la cuenta), valor anterior, valor nuevo y motivo.
# 2. Los registros que ya existían toman el autor de su usuario, si lo tienen.
# 3. En PostgreSQL, un trigger rechaza borrar o modificar un registro. La única
#    modificación permitida es la que hace la base sola al borrar una cuenta:
#    poner usuario_id en NULL (on_delete=SET_NULL) sin tocar nada más. En
#    SQLite (desarrollo y tests locales) lo impide solo el modelo.

from django.db import migrations, models

FUNCION = 'auditoria_inmodificable'
TRIGGER = 'auditoria_inmodificable'

COLUMNAS_FIJAS = (
    'id', 'autor_dni', 'autor_nombre', 'autor_rol', 'accion', 'modelo_afectado',
    'objeto_id', 'valor_anterior', 'valor_nuevo', 'motivo', 'fecha',
)


def completar_autor(apps, schema_editor):
    RegistroAuditoria = apps.get_model('inscripcionFinales', 'RegistroAuditoria')
    for registro in RegistroAuditoria.objects.filter(usuario__isnull=False).select_related('usuario'):
        usuario = registro.usuario
        RegistroAuditoria.objects.filter(pk=registro.pk).update(
            autor_dni='' if usuario.dni is None else str(usuario.dni),
            autor_nombre=usuario.nombre_completo or usuario.email or '',
            autor_rol=usuario.rol or '',
        )


def crear_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    tabla = schema_editor.quote_name(apps.get_model('inscripcionFinales', 'RegistroAuditoria')._meta.db_table)
    nuevas = ', '.join(f'NEW.{c}' for c in COLUMNAS_FIJAS)
    viejas = ', '.join(f'OLD.{c}' for c in COLUMNAS_FIJAS)
    schema_editor.execute(f"""
        CREATE OR REPLACE FUNCTION {FUNCION}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Los registros de auditoría no se borran (#271).';
            END IF;
            -- Al borrar una cuenta, SET_NULL deja usuario_id en NULL: es lo
            -- único que puede cambiar, y el autor sigue en autor_dni/nombre/rol.
            IF NEW.usuario_id IS NULL AND OLD.usuario_id IS NOT NULL
               AND ROW({nuevas}) IS NOT DISTINCT FROM ROW({viejas}) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Los registros de auditoría no se modifican (#271).';
        END;
        $$ LANGUAGE plpgsql;
    """)
    schema_editor.execute(f'DROP TRIGGER IF EXISTS {TRIGGER} ON {tabla};')
    schema_editor.execute(
        f'CREATE TRIGGER {TRIGGER} BEFORE UPDATE OR DELETE ON {tabla} '
        f'FOR EACH ROW EXECUTE FUNCTION {FUNCION}();'
    )


def borrar_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    tabla = schema_editor.quote_name(apps.get_model('inscripcionFinales', 'RegistroAuditoria')._meta.db_table)
    schema_editor.execute(f'DROP TRIGGER IF EXISTS {TRIGGER} ON {tabla};')
    schema_editor.execute(f'DROP FUNCTION IF EXISTS {FUNCION}();')


class Migration(migrations.Migration):

    dependencies = [
        ('inscripcionFinales', '0023_alter_usuarios_materia_ciclo_actual_desde'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroauditoria',
            name='autor_dni',
            field=models.CharField(blank=True, max_length=20, verbose_name='DNI del autor'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='autor_nombre',
            field=models.CharField(blank=True, max_length=255, verbose_name='Autor'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='autor_rol',
            field=models.CharField(blank=True, max_length=20, verbose_name='Rol del autor'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='motivo',
            field=models.TextField(blank=True, verbose_name='Motivo'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='valor_anterior',
            field=models.TextField(blank=True, verbose_name='Valor anterior'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='valor_nuevo',
            field=models.TextField(blank=True, verbose_name='Valor nuevo'),
        ),
        migrations.RunPython(completar_autor, migrations.RunPython.noop),
        migrations.RunPython(crear_trigger, borrar_trigger),
    ]
