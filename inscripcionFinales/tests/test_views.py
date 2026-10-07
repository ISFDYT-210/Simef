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
    Carrera, EstadoCursada, InscripcionFinal, Materia, MesaFinal, TribunalMesa, Usuario, usuarios_materia,
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


class EliminarInscripcionMateriaTest(TestCase):
    """
    Dar de baja una materia es administrativo: el alumno no puede
    autogestionarlo, solo Preceptor/Directivo/Secretario (ver puede_administrar).
    No borra el registro: lo marca ABANDONO para preservar el historial.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=carrera, anio=1)

        cls.alumno = crear_usuario('alu_baja@test.com', 'Estudiante', 'Alumno', 30)
        cls.preceptor = crear_usuario('prec_baja@test.com', 'Preceptor', 'Preceptora', 31)
        cls.profesor = crear_usuario('prof_baja@test.com', 'Profesor', 'Profesor', 32)

    def setUp(self):
        self.inscripcion = usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia)
        self.url = f'/eliminar_inscripcion_materia/{self.inscripcion.id}/'

    def test_el_alumno_no_puede_darse_de_baja_el_mismo(self):
        self.client.force_login(self.alumno)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, EstadoCursada.EN_CURSO)

    def test_el_profesor_no_puede_dar_de_baja(self):
        self.client.force_login(self.profesor)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, EstadoCursada.EN_CURSO)

    def test_el_preceptor_puede_dar_de_baja_y_queda_marcado_como_abandono(self):
        self.client.force_login(self.preceptor)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, EstadoCursada.ABANDONO)


class InscripcionExcepcionalMesaTest(TestCase):
    """
    Inscripción excepcional: Preceptor/Directivo/Secretario puede inscribir a
    un alumno aunque la ventana normal esté cerrada, siempre que falten al
    menos MesaFinal.LIMITE_DIAS_EXCEPCION días para el examen. No bypassea
    los requisitos académicos (nota de cursada, correlativas).
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        # anio=2 para que la señal de alta en bloque de primer año no cree
        # una segunda fila de usuarios_materia por su cuenta.
        cls.materia = Materia.objects.create(nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        cls.preceptor = crear_usuario('prec_exc@test.com', 'Preceptor', 'Preceptora', 40)
        cls.alumno = crear_usuario('alu_exc@test.com', 'Estudiante', 'Alumno', 41)
        cls.alumno.carrera.add(cls.carrera)

    def mesa_cerrada(self, dias):
        """inscripcionAbierta=False: la ventana normal nunca se abrió."""
        return MesaFinal.objects.create(
            materia=self.materia, llamado=timezone.now() + timedelta(days=dias),
            inscripcionAbierta=False,
        )

    def test_obtener_finales_marca_excepcional_si_cumple_academico_y_hay_margen(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        mesa = self.mesa_cerrada(dias=5)
        self.client.force_login(self.preceptor)
        datos = self.client.get(f'/obtener_finales_estudiante/?estudiante_id={self.alumno.id}').json()
        self.assertEqual(datos['status'], 'success')
        self.assertEqual(len(datos['finales']), 1)
        self.assertEqual(datos['finales'][0]['id'], mesa.id)
        self.assertTrue(datos['finales'][0]['excepcional'])

    def test_obtener_finales_no_ofrece_excepcional_si_falta_poco_para_el_examen(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        self.mesa_cerrada(dias=1)
        self.client.force_login(self.preceptor)
        datos = self.client.get(f'/obtener_finales_estudiante/?estudiante_id={self.alumno.id}').json()
        self.assertEqual(datos['finales'], [])

    def test_obtener_finales_no_ofrece_excepcional_si_no_cumple_requisito_academico(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=5)  # < 7
        self.mesa_cerrada(dias=5)
        self.client.force_login(self.preceptor)
        datos = self.client.get(f'/obtener_finales_estudiante/?estudiante_id={self.alumno.id}').json()
        self.assertEqual(datos['finales'], [])

    def test_inscribir_excepcional_funciona_con_margen(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        mesa = self.mesa_cerrada(dias=5)
        self.client.force_login(self.preceptor)
        respuesta = self.client.post('/inscribir_final/', {
            'usuario': self.alumno.id, 'llamado': mesa.id, 'excepcional': 'true',
        }).json()
        self.assertEqual(respuesta['status'], 'success')
        self.assertTrue(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=mesa).exists())

    def test_inscribir_excepcional_falla_si_falta_poco_para_el_examen(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        mesa = self.mesa_cerrada(dias=1)
        self.client.force_login(self.preceptor)
        respuesta = self.client.post('/inscribir_final/', {
            'usuario': self.alumno.id, 'llamado': mesa.id, 'excepcional': 'true',
        }).json()
        self.assertEqual(respuesta['status'], 'error')
        self.assertFalse(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=mesa).exists())

    def test_sin_excepcional_la_mesa_cerrada_sigue_rechazando(self):
        """excepcional=False (o ausente) respeta la regla normal, sin cambios de comportamiento."""
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        mesa = self.mesa_cerrada(dias=5)
        self.client.force_login(self.preceptor)
        respuesta = self.client.post('/inscribir_final/', {
            'usuario': self.alumno.id, 'llamado': mesa.id,
        }).json()
        self.assertEqual(respuesta['status'], 'error')


class TribunalMesaTest(TestCase):
    """
    Asignación de tribunal: Preceptor asigna Presidente/Vocales, puede
    reemplazar a uno sin tocar el resto, y un mismo docente puede figurar en
    tribunales de mesas distintas en simultáneo (no se valida solapamiento).
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=carrera, anio=1)
        cls.otra_materia = Materia.objects.create(nombre_materia='Matemática I', carrera=carrera, anio=1)
        cls.preceptor = crear_usuario('prec_trib@test.com', 'Preceptor', 'Preceptora', 60)
        cls.profesor1 = crear_usuario('prof_trib1@test.com', 'Profesor', 'Profesor Uno', 61)
        cls.profesor2 = crear_usuario('prof_trib2@test.com', 'Profesor', 'Profesor Dos', 62)
        cls.profesor3 = crear_usuario('prof_trib3@test.com', 'Profesor', 'Profesor Tres', 63)

    def setUp(self):
        self.mesa = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() + timedelta(days=5))
        self.url = f'/tribunal_mesa/{self.mesa.id}/'
        self.client.force_login(self.preceptor)

    def test_asigna_presidente(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Presidente'})
        tribunal = TribunalMesa.objects.get(mesa=self.mesa, activo=True)
        self.assertEqual(tribunal.docente, self.profesor1)
        self.assertEqual(tribunal.rol, 'Presidente')

    def test_no_permite_dos_presidentes_activos(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Presidente'})
        self.client.post(self.url, {'docente': self.profesor2.id, 'rol': 'Presidente'})
        self.assertEqual(TribunalMesa.objects.filter(mesa=self.mesa, rol='Presidente', activo=True).count(), 1)

    def test_no_permite_mas_vocales_que_el_maximo(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Vocal'})
        self.client.post(self.url, {'docente': self.profesor2.id, 'rol': 'Vocal'})
        self.client.post(self.url, {'docente': self.profesor3.id, 'rol': 'Vocal'})
        self.assertEqual(TribunalMesa.objects.filter(mesa=self.mesa, rol='Vocal', activo=True).count(), 2)

    def test_reemplazar_desactiva_al_anterior_y_conserva_el_historial(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Vocal'})
        original = TribunalMesa.objects.get(mesa=self.mesa, docente=self.profesor1)

        self.client.post(f'/reemplazar_tribunal/{original.id}/', {'docente': self.profesor2.id})

        original.refresh_from_db()
        self.assertFalse(original.activo)
        nuevo = TribunalMesa.objects.get(mesa=self.mesa, activo=True, rol='Vocal')
        self.assertEqual(nuevo.docente, self.profesor2)
        self.assertEqual(nuevo.reemplaza_a, original)

    def test_quitar_sin_reemplazo_deja_el_puesto_vacante(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Vocal'})
        asignacion = TribunalMesa.objects.get(mesa=self.mesa, docente=self.profesor1)

        self.client.post(f'/quitar_tribunal/{asignacion.id}/')

        asignacion.refresh_from_db()
        self.assertFalse(asignacion.activo)
        self.assertEqual(TribunalMesa.objects.filter(mesa=self.mesa, activo=True).count(), 0)

    def test_un_docente_puede_estar_en_tribunales_de_mesas_simultaneas(self):
        """Mesas paralelas en el mismo horario: no se valida solapamiento a propósito."""
        otra_mesa = MesaFinal.objects.create(materia=self.otra_materia, llamado=self.mesa.llamado)
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Presidente'})
        self.client.post(f'/tribunal_mesa/{otra_mesa.id}/', {'docente': self.profesor1.id, 'rol': 'Presidente'})
        self.assertEqual(TribunalMesa.objects.filter(docente=self.profesor1, activo=True).count(), 2)

    def test_acta_volante_muestra_el_tribunal_asignado(self):
        self.client.post(self.url, {'docente': self.profesor1.id, 'rol': 'Presidente'})
        self.client.post(self.url, {'docente': self.profesor2.id, 'rol': 'Vocal'})
        respuesta = self.client.get(f'/acta_volante/{self.mesa.id}')
        contenido = respuesta.content.decode()
        self.assertIn('Profesor Uno', contenido)
        self.assertIn('Profesor Dos', contenido)
