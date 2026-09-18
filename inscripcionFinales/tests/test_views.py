"""
Tests de los listados que se cargan por JSON (api_* en views.py).

Lo que más importa acá es el filtrado por rol de api_finales_inscriptos_adm:
un profesor tiene que ver únicamente a sus propios alumnos. Es una propiedad
de privacidad que no se nota si se rompe —la página sigue mostrando una tabla
llena— así que conviene tenerla cubierta.

Correr con:
    python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
"""
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from inscripcionFinales.models import (
    Carrera, InscripcionFinal, Materia, MesaFinal, Usuario, usuarios_materia,
)


def crear_usuario(email, rol, nombre, dni, **extra):
    """first_login=False evita que el middleware redirija al cambio de contraseña."""
    usuario = Usuario.objects.create(
        email=email, username=email.split('@')[0], nombre_completo=nombre,
        rol=rol, dni=dni, first_login=False, **extra
    )
    usuario.set_password('secreta')
    usuario.save()
    return usuario


class FinalesInscriptosAdmAPITest(TestCase):
    """api_finales_inscriptos_adm: permisos, filtrado por rol y notas."""

    @classmethod
    def setUpTestData(cls):
        cls.url = '/api/finales_inscriptos_adm/'

        cls.directivo = crear_usuario('dir@test.com', 'Directivo', 'Directiva', 1)
        cls.profe_propio = crear_usuario('p1@test.com', 'Profesor', 'Profe Propio', 2)
        cls.profe_ajeno = crear_usuario('p2@test.com', 'Profesor', 'Profe Ajeno', 3)
        cls.estudiante = crear_usuario('est@test.com', 'Estudiante', 'Estudiante Uno', 4)

        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia_propia = Materia.objects.create(
            nombre_materia='Matemática Aplicada', carrera=carrera, anio=1,
            profesor=cls.profe_propio,
        )
        cls.materia_ajena = Materia.objects.create(
            nombre_materia='Historia', carrera=carrera, anio=2,
            profesor=cls.profe_ajeno,
        )

        futuro = timezone.now() + timedelta(days=10)
        mesa_propia = MesaFinal.objects.create(materia=cls.materia_propia, llamado=futuro)
        mesa_ajena = MesaFinal.objects.create(materia=cls.materia_ajena, llamado=futuro)

        InscripcionFinal.objects.create(usuario=cls.estudiante, llamado=mesa_propia, aprobada=None)
        InscripcionFinal.objects.create(usuario=cls.estudiante, llamado=mesa_ajena, aprobada=None)

    def test_estudiante_no_accede(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonimo_no_accede(self):
        # login_required redirige; lo que importa es que no devuelva los datos
        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_directivo_ve_todas_las_inscripciones(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()
        self.assertEqual(datos['count'], 2)

    def test_profesor_solo_ve_sus_propios_alumnos(self):
        """Si esto se rompe, un profesor pasa a ver los alumnos de toda la escuela."""
        self.client.force_login(self.profe_propio)
        datos = self.client.get(self.url).json()

        self.assertEqual(datos['count'], 1)
        materias = [fila['materia'] for fila in datos['results']]
        self.assertEqual(materias, ['Matemática Aplicada'])
        self.assertNotIn('Historia', materias)

    def test_profesor_sin_alumnos_no_ve_nada(self):
        otro = crear_usuario('p3@test.com', 'Profesor', 'Profe Sin Mesas', 5)
        self.client.force_login(otro)
        self.assertEqual(self.client.get(self.url).json()['count'], 0)

    def test_busqueda_filtra_por_materia_y_por_estudiante(self):
        self.client.force_login(self.directivo)

        por_materia = self.client.get(self.url, {'q': 'Historia'}).json()
        self.assertEqual([f['materia'] for f in por_materia['results']], ['Historia'])

        por_estudiante = self.client.get(self.url, {'q': 'Estudiante Uno'}).json()
        self.assertEqual(por_estudiante['count'], 2)

        sin_resultados = self.client.get(self.url, {'q': 'no-existe'}).json()
        self.assertEqual(sin_resultados['count'], 0)

    def test_nota_de_cursada_no_se_confunde_con_la_de_final(self):
        """Cada fila trae la nota de SU par (estudiante, materia), no la de otra."""
        usuarios_materia.objects.create(
            usuario=self.estudiante, materia=self.materia_propia,
            nota_cursada=8, nota_final=7,
        )
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()

        por_materia = {f['materia']: f['notas'] for f in datos['results']}
        self.assertEqual(por_materia['Matemática Aplicada'], [7])
        self.assertEqual(por_materia['Historia'], [])

    def test_no_hace_una_query_por_fila(self):
        """
        El N+1 que motivó el refactor: la cantidad de queries tiene que ser la
        misma con 2 inscripciones que con 10. Comparamos las dos medidas en vez
        de fijar un número exacto, que se rompería por cualquier cambio ajeno
        (una query de sesión, un middleware nuevo).
        """
        self.client.force_login(self.directivo)

        with CaptureQueriesContext(connection) as con_pocas:
            self.client.get(self.url)

        futuro = timezone.now() + timedelta(days=10)
        for i in range(8):
            materia = Materia.objects.create(
                nombre_materia=f'Relleno {i}', carrera=self.materia_propia.carrera, anio=1)
            mesa = MesaFinal.objects.create(materia=materia, llamado=futuro)
            otro = crear_usuario(f'relleno{i}@test.com', 'Estudiante', f'Relleno {i}', 900 + i)
            InscripcionFinal.objects.create(usuario=otro, llamado=mesa, aprobada=None)

        with CaptureQueriesContext(connection) as con_muchas:
            respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.json()['results']), 10)
        self.assertEqual(len(con_muchas), len(con_pocas))


class ListaMesasAPITest(TestCase):
    """api_lista_mesas: permisos, búsqueda sin tildes y estado de inscripción."""

    @classmethod
    def setUpTestData(cls):
        cls.url = '/api/mesas/'
        cls.directivo = crear_usuario('dir2@test.com', 'Directivo', 'Directiva', 10)
        cls.estudiante = crear_usuario('est2@test.com', 'Estudiante', 'Estudiante', 11)

        carrera = Carrera.objects.create(nombre_carrera='Profesorado')
        materia = Materia.objects.create(
            nombre_materia='Matemática Aplicada', carrera=carrera, anio=1,
        )
        cls.mesa_vigente = MesaFinal.objects.create(
            materia=materia, llamado=timezone.now() + timedelta(days=5),
            inscripcionAbierta=True,
        )
        cls.mesa_vencida = MesaFinal.objects.create(
            materia=materia, llamado=timezone.now() - timedelta(days=5),
            inscripcionAbierta=True,
        )
        cls.mesa_cerrada = MesaFinal.objects.create(
            materia=materia, llamado=timezone.now() + timedelta(days=5),
            inscripcionAbierta=False,
        )

    def test_estudiante_no_accede(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_busqueda_ignora_tildes(self):
        """Escribir 'matematica' sin tilde tiene que encontrar 'Matemática'."""
        self.client.force_login(self.directivo)
        for termino in ('matematica', 'Matemática', 'MATEMATICA'):
            with self.subTest(termino=termino):
                datos = self.client.get(self.url, {'q': termino}).json()
                self.assertEqual(datos['count'], 3)

    def test_busqueda_sin_coincidencias(self):
        self.client.force_login(self.directivo)
        self.assertEqual(self.client.get(self.url, {'q': 'quimica'}).json()['count'], 0)

    def test_distingue_vigente_vencida_y_cerrada(self):
        """La UI muestra tres estados distintos y necesita los dos campos."""
        self.client.force_login(self.directivo)
        filas = {f['id']: f for f in self.client.get(self.url).json()['results']}

        self.assertTrue(filas[self.mesa_vigente.id]['vigente'])

        # Habilitada a mano pero con la fecha ya pasada -> "Vencida"
        self.assertFalse(filas[self.mesa_vencida.id]['vigente'])
        self.assertTrue(filas[self.mesa_vencida.id]['abierta'])

        self.assertFalse(filas[self.mesa_cerrada.id]['vigente'])
        self.assertFalse(filas[self.mesa_cerrada.id]['abierta'])

    def test_pagina_de_a_diez(self):
        carrera = Carrera.objects.get(nombre_carrera='Profesorado')
        materia = Materia.objects.create(nombre_materia='Relleno', carrera=carrera, anio=1)
        for _ in range(12):
            MesaFinal.objects.create(materia=materia, llamado=timezone.now() + timedelta(days=3))

        self.client.force_login(self.directivo)
        primera = self.client.get(self.url).json()
        self.assertEqual(len(primera['results']), 10)
        self.assertEqual(primera['count'], 15)
        self.assertEqual(primera['num_pages'], 2)

        segunda = self.client.get(self.url, {'page': 2}).json()
        self.assertEqual(len(segunda['results']), 5)

        # Ninguna mesa aparece en las dos páginas
        ids_primera = {f['id'] for f in primera['results']}
        ids_segunda = {f['id'] for f in segunda['results']}
        self.assertEqual(ids_primera & ids_segunda, set())


class ListaInscripcionesAPITest(TestCase):
    """api_lista_inscripciones: solo personal administrativo."""

    @classmethod
    def setUpTestData(cls):
        cls.url = '/api/inscripciones/'
        cls.directivo = crear_usuario('dir3@test.com', 'Directivo', 'Directiva', 20)
        cls.estudiante = crear_usuario('est3@test.com', 'Estudiante', 'Estudiante', 21)

        carrera = Carrera.objects.create(nombre_carrera='Carrera')
        materia = Materia.objects.create(nombre_materia='Materia', carrera=carrera, anio=1)
        mesa = MesaFinal.objects.create(materia=materia, llamado=timezone.now() + timedelta(days=4))
        InscripcionFinal.objects.create(usuario=cls.estudiante, llamado=mesa, aprobada=None)

    def test_estudiante_no_accede(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_directivo_ve_las_inscripciones(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()
        self.assertEqual(datos['count'], 1)
        self.assertEqual(datos['results'][0]['usuario'], 'Estudiante')
