"""
Compara la base de datos real con el código (CICD-12).

Los tests arman la base desde las migraciones del repo, así que no ven lo que
la base de producción tiene distinto. Así pasó con la columna `ausente`: Neon
la tenía como obligatoria, ningún modelo la conocía, y cada inscripción a
final fallaba (CICD-05). Este comando se corre contra la base de destino antes
de desplegar, y después de migrar (ver scripts/migrar_neon.sh):

    python manage.py verificar_esquema                  # antes de migrar
    python manage.py verificar_esquema --sin-pendientes # después de migrar

Errores (el comando termina con código distinto de 0):
- Migraciones registradas en la base que no están en el repo, salvo las
  conocidas de MIGRACIONES_CONOCIDAS.
- Tablas o columnas que el código espera y la base no tiene.
- Columnas que la base tiene y el código no, si son obligatorias y sin valor
  por defecto: rompen cualquier alta en esa tabla.
- Migraciones sin aplicar, solo con --sin-pendientes.

Avisos: migraciones sin aplicar (sin --sin-pendientes) y columnas de más que
no rompen nada. Solo lee la base: no escribe nada.
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# Migraciones que una base puede tener registradas sin que estén en el repo,
# con el motivo. Cada una tiene que estar justificada en el decision log.
MIGRACIONES_CONOCIDAS = {
    ('inscripcionFinales', '0009_inscripcionfinal_ausente'): (
        'Se aplicó en Neon desde una rama el 06/10 y nunca llegó al repo. '
        'La 0016 adopta su columna (decision log D-02 y D-08).'
    ),
}


class Command(BaseCommand):
    help = 'Compara las migraciones y las columnas de la base real con el código.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-pendientes', action='store_true',
            help='Falla si quedan migraciones sin aplicar (para después de migrar).',
        )

    def handle(self, *args, **options):
        errores, avisos = [], []
        executor = MigrationExecutor(connection)
        loader = executor.loader

        # 1. Migraciones registradas en la base que el repo no tiene.
        en_repo = set(loader.disk_migrations)
        for app, nombre in sorted(loader.applied_migrations):
            if (app, nombre) in en_repo:
                continue
            if app not in loader.migrated_apps:
                avisos.append(f'Migración registrada de una app que ya no está instalada: {app}.{nombre}')
            elif (app, nombre) in MIGRACIONES_CONOCIDAS:
                avisos.append(f'Migración fuera del repo, conocida: {app}.{nombre}. '
                              f'{MIGRACIONES_CONOCIDAS[(app, nombre)]}')
            else:
                errores.append(f'La base tiene registrada {app}.{nombre}, que no está en el repo. '
                               'Alguien migró desde una rama: averiguar qué cambió antes de desplegar.')

        # 2. Migraciones del repo sin aplicar.
        pendientes = executor.migration_plan(loader.graph.leaf_nodes())
        apps_pendientes = {migracion.app_label for migracion, _ in pendientes}
        if pendientes:
            nombres = ', '.join(f'{m.app_label}.{m.name}' for m, _ in pendientes)
            mensaje = f'{len(pendientes)} migraciones sin aplicar: {nombres}'
            (errores if options['sin_pendientes'] else avisos).append(mensaje)

        # 3. Columnas, solo de las apps sin migraciones pendientes: en las
        #    otras, la diferencia es la que esas migraciones van a resolver.
        with connection.cursor() as cursor:
            tablas = set(connection.introspection.table_names(cursor))
            for modelo in apps.get_models(include_auto_created=True):
                meta = modelo._meta
                if not meta.managed or meta.proxy or meta.app_label in apps_pendientes:
                    continue
                tabla = meta.db_table
                if tabla not in tablas:
                    errores.append(f'Falta la tabla {tabla} ({meta.label}).')
                    continue
                esperadas = {campo.column for campo in meta.local_concrete_fields}
                reales = {c.name: c for c in connection.introspection.get_table_description(cursor, tabla)}
                for columna in sorted(esperadas - set(reales)):
                    errores.append(f'Falta la columna {tabla}.{columna}, que el código usa.')
                for columna in sorted(set(reales) - esperadas):
                    info = reales[columna]
                    if not info.null_ok and info.default is None:
                        errores.append(f'La base tiene la columna obligatoria {tabla}.{columna} sin valor por '
                                       'defecto, y el código no la conoce: toda alta en esa tabla va a fallar.')
                    else:
                        avisos.append(f'La base tiene la columna {tabla}.{columna}, que el código no usa.')

        if apps_pendientes:
            avisos.append('Columnas sin comparar en: ' + ', '.join(sorted(apps_pendientes))
                          + ' (tienen migraciones pendientes).')
        for aviso in avisos:
            self.stdout.write(self.style.WARNING('AVISO  ') + aviso)
        for error in errores:
            self.stdout.write(self.style.ERROR('ERROR  ') + error)
        if errores:
            raise CommandError(f'El esquema de la base no coincide con el código: {len(errores)} error(es).')
        self.stdout.write(self.style.SUCCESS('El esquema de la base coincide con el código.'))
