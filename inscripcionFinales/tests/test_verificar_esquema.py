"""
Tests del comando verificar_esquema (CICD-12).

Cada caso altera la base de tests dentro de la transacción del test (en
PostgreSQL el DDL también se revierte) y comprueba que el comando lo detecte.
El primero reproduce el problema real de la columna `ausente` (CICD-05).
"""
from io import StringIO

from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from inscripcionFinales.management.commands.verificar_esquema import MIGRACIONES_CONOCIDAS

TABLA = '"inscripcionFinales_inscripcionfinal"'


def verificar(*args):
    salida = StringIO()
    call_command('verificar_esquema', *args, stdout=salida)
    return salida.getvalue()


class VerificarEsquemaTest(TestCase):

    def ejecutar(self, sql, params=None):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    def test_una_base_migrada_desde_el_repo_coincide(self):
        self.assertIn('coincide con el código', verificar('--sin-pendientes'))

    def test_detecta_una_columna_obligatoria_que_el_codigo_no_conoce(self):
        # Lo que pasó con `ausente` en Neon: toda inscripción a final fallaba.
        self.ejecutar(f'ALTER TABLE {TABLA} ADD COLUMN columna_fantasma boolean NOT NULL')
        with self.assertRaises(CommandError):
            verificar()

    def test_una_columna_de_mas_que_no_rompe_altas_es_solo_aviso(self):
        self.ejecutar(f'ALTER TABLE {TABLA} ADD COLUMN columna_opcional text NULL')
        salida = verificar()
        self.assertIn('AVISO', salida)
        self.assertIn('columna_opcional', salida)

    def test_detecta_una_columna_que_falta(self):
        self.ejecutar(f'ALTER TABLE {TABLA} DROP COLUMN nota')
        with self.assertRaises(CommandError):
            verificar()

    def test_detecta_una_migracion_aplicada_desde_una_rama(self):
        self.ejecutar(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
            ['inscripcionFinales', '0099_migracion_de_una_rama', timezone.now()],
        )
        with self.assertRaises(CommandError):
            verificar()

    def test_una_migracion_conocida_fuera_del_repo_es_solo_aviso(self):
        app, nombre = next(iter(MIGRACIONES_CONOCIDAS))
        self.ejecutar(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)", [app, nombre, timezone.now()])
        salida = verificar('--sin-pendientes')
        self.assertIn('conocida', salida)
        self.assertIn('coincide con el código', salida)

    def test_con_sin_pendientes_una_migracion_sin_aplicar_es_error(self):
        self.ejecutar(
            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
            ['inscripcionFinales', '0023_alter_usuarios_materia_ciclo_actual_desde'],
        )
        self.assertIn('sin aplicar', verificar())
        with self.assertRaises(CommandError):
            verificar('--sin-pendientes')
