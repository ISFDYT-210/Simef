import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inscripcionFinales.models import Carrera, Materia


def parse_tuples(text):
    """Parsea una lista de tuplas literales de un VALUES(...) de Postgres.

    Soporta enteros, NULL y strings entre comillas simples con '' como
    escape de comilla (sintaxis estándar de Postgres).
    """
    tuples = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1
        values = []
        while True:
            while i < n and text[i] in ' \t\n\r':
                i += 1
            if text[i] == "'":
                i += 1
                buf = []
                while True:
                    if text[i] == "'":
                        if i + 1 < n and text[i + 1] == "'":
                            buf.append("'")
                            i += 2
                            continue
                        break
                    buf.append(text[i])
                    i += 1
                values.append(''.join(buf))
                i += 1
            else:
                start = i
                while i < n and text[i] not in ',)':
                    i += 1
                token = text[start:i].strip()
                values.append(None if token == 'NULL' else int(token))
            while i < n and text[i] in ' \t\n\r':
                i += 1
            if text[i] == ',':
                i += 1
                continue
            elif text[i] == ')':
                i += 1
                break
        tuples.append(values)
        while i < n and text[i] in ' \t\n\r,':
            i += 1
        if i < n and text[i] == ';':
            break
    return tuples


def extract_values_section(sql, marker):
    start = sql.index(marker) + len(marker)
    end = sql.index(';', start)
    return sql[start:end]


class Command(BaseCommand):
    help = (
        'Carga carreras y materias desde un dump tipo carga_datos_neon.sql '
        '(pensado para el esquema viejo/Neon) hacia el esquema actual de Simef '
        '(Carrera.nombre_carrera, Materia.nombre_materia/anio) usando el ORM. '
        'Ignora columnas que no existen en el modelo actual (campo_formacion, '
        'carga_horaria, formato) y deja Materia.profesor en null, ya que los '
        '"profesores" del dump son solo nombres sueltos sin cuenta de usuario.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=os.path.expanduser('~/Descargas/carga_datos_neon.sql'),
            help='Ruta al archivo .sql a importar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se crearía sin escribir en la base de datos',
        )

    def handle(self, *args, **options):
        path = options['path']
        dry_run = options['dry_run']

        if not os.path.isfile(path):
            raise CommandError(f'No se encontró el archivo: {path}')

        with open(path, encoding='utf-8') as f:
            sql = f.read()

        carreras_section = extract_values_section(
            sql, 'INSERT INTO inscripcionFinales_carreras (id, nombre) VALUES'
        )
        materias_section = extract_values_section(
            sql,
            'INSERT INTO inscripcionFinales_materias '
            '(id, nombre, ano, campo_formacion, carga_horaria, formato, carrera_id, profesor_id) VALUES',
        )

        carreras_rows = parse_tuples(carreras_section)
        materias_rows = parse_tuples(materias_section)

        self.stdout.write(f'{len(carreras_rows)} carreras y {len(materias_rows)} materias encontradas en el archivo.')

        carreras_creadas = 0
        carreras_existentes = 0
        materias_creadas = 0
        materias_existentes = 0
        materias_sin_carrera = []

        with transaction.atomic():
            carrera_id_map = {}
            for old_id, nombre in carreras_rows:
                carrera, created = Carrera.objects.get_or_create(nombre_carrera=nombre)
                carrera_id_map[old_id] = carrera
                if created:
                    carreras_creadas += 1
                else:
                    carreras_existentes += 1

            for old_id, nombre, ano, campo_formacion, carga_horaria, formato, carrera_id, profesor_id in materias_rows:
                carrera = carrera_id_map.get(carrera_id)
                if carrera is None:
                    materias_sin_carrera.append((old_id, nombre))
                    continue

                anio_num = int(ano[0]) if ano and ano[0].isdigit() else 1

                materia, created = Materia.objects.get_or_create(
                    nombre_materia=nombre,
                    carrera=carrera,
                    defaults={'anio': anio_num},
                )
                if created:
                    materias_creadas += 1
                else:
                    materias_existentes += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'Carreras: {carreras_creadas} creadas, {carreras_existentes} ya existían.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Materias: {materias_creadas} creadas, {materias_existentes} ya existían.'
        ))
        if materias_sin_carrera:
            self.stdout.write(self.style.WARNING(
                f'{len(materias_sin_carrera)} materias omitidas por carrera_id desconocido: {materias_sin_carrera[:10]}'
            ))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: no se guardó nada (rollback).'))
