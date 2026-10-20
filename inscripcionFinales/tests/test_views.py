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

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from inscripcionFinales.models import (
    Carrera, EstadoCursada, InscripcionFinal, Materia, MateriaCorrelativa, MesaFinal, TribunalMesa, Usuario,
    usuarios_materia,
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
        # La mesa de este llamado ya pasó: recién ahí tiene sentido mostrar
        # la nota por el camino de compatibilidad (sin InscripcionFinal.nota).
        mesa_pasada = MesaFinal.objects.create(
            materia=self.materia_propia, llamado=timezone.now() - timedelta(days=1))
        InscripcionFinal.objects.create(usuario=self.estudiante, llamado=mesa_pasada, aprobada=False)

        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()

        por_materia = {f['materia']: f['notas'] for f in datos['results'] if f['mesa_id'] == mesa_pasada.id}
        self.assertEqual(por_materia['Matemática Aplicada'], [7])

    def test_nota_por_intento_no_depende_de_usuarios_materia(self):
        """InscripcionFinal.nota es la fuente de verdad del llamado; no hace
        falta el truco de 'mesa futura' para evitar la nota de otro intento."""
        mesa_pasada = MesaFinal.objects.create(
            materia=self.materia_propia, llamado=timezone.now() - timedelta(days=1))
        InscripcionFinal.objects.create(usuario=self.estudiante, llamado=mesa_pasada, aprobada=False, nota=9)

        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()

        fila = next(f for f in datos['results'] if f['mesa_id'] == mesa_pasada.id)
        self.assertEqual(fila['notas'], [9])
        self.assertFalse(fila['ausente'])

    def test_ausente_se_informa_en_el_json(self):
        InscripcionFinal.objects.filter(usuario=self.estudiante, llamado__materia=self.materia_propia).update(ausente=True)
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()
        fila = next(f for f in datos['results'] if f['materia'] == 'Matemática Aplicada')
        self.assertTrue(fila['ausente'])

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

    def test_informa_aula_y_sede(self):
        self.mesa_vigente.aula = 'Aula 3'
        self.mesa_vigente.sede = 'Sede central'
        self.mesa_vigente.save()
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()
        fila = next(f for f in datos['results'] if f['id'] == self.mesa_vigente.id)
        self.assertEqual(fila['aula'], 'Aula 3')
        self.assertEqual(fila['sede'], 'Sede central')

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


class InscripcionFinalEstudianteTest(TestCase):
    """
    inscripcionFinalEst: el alumno se inscribe solo desde /inscribirse_final/<id>.

    La vista le pasaba a validar_inscripcion_final() la Materia entera en vez de
    su id, y la consulta usuarios_materia.objects.get(materia_id=...) explotaba
    con TypeError: ningún alumno podía inscribirse a un final por su cuenta.

    Requiere POST (SEC-09): un GET que mutara acá se podía disparar con un
    simple link o <img> de un sitio externo sin que el alumno lo pidiera.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        # anio=2 por el mismo motivo que en InscripcionExcepcionalMesaTest.
        cls.materia = Materia.objects.create(nombre_materia='Psicología', carrera=carrera, anio=2)
        cls.alumno = crear_usuario('alu_est@test.com', 'Estudiante', 'Alumno', 50)
        cls.alumno.carrera.add(carrera)
        cls.mesa = MesaFinal.objects.create(
            materia=cls.materia, llamado=timezone.now() + timedelta(days=5),
            inscripcionAbierta=True,
        )
        cls.url = f'/inscribirse_final/{cls.mesa.id}'

    def test_alumno_que_cumple_los_requisitos_queda_inscripto(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        self.client.force_login(self.alumno)
        respuesta = self.client.post(self.url)
        self.assertRedirects(respuesta, '/inscripcionFinalEst/', fetch_redirect_response=False)
        self.assertTrue(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=self.mesa).exists())

    def test_la_inscripcion_nueva_queda_como_presente(self):
        """
        La columna ausente es NOT NULL y sin default en la base (#119): si el
        modelo deja de mandarla en el INSERT, la inscripción vuelve a fallar
        con IntegrityError.
        """
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        self.client.force_login(self.alumno)
        self.client.post(self.url)
        inscripcion = InscripcionFinal.objects.get(usuario=self.alumno, llamado=self.mesa)
        self.assertFalse(inscripcion.ausente)

    def test_el_rechazo_dice_el_motivo_concreto(self):
        """El mismo motivo que muestra la lista de finales (#134, #103)."""
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=5)
        self.client.force_login(self.alumno)
        respuesta = self.client.post(self.url, follow=True)
        mensajes = [str(m) for m in respuesta.context['messages']]
        self.assertIn('No puedes inscribirte en este final: Necesitás nota de cursada ≥ 7 (o modalidad libre).',
                      mensajes)

    def test_un_get_responde_405_y_no_inscribe(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertFalse(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=self.mesa).exists())

    def test_alumno_que_no_cumple_los_requisitos_no_queda_inscripto(self):
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=5)  # < 7
        self.client.force_login(self.alumno)
        respuesta = self.client.post(self.url)
        self.assertRedirects(respuesta, '/inscripcionFinalEst/', fetch_redirect_response=False)
        self.assertFalse(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=self.mesa).exists())


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


class AltaMesaFinalSinDuplicadosTest(TestCase):
    """
    No se puede cargar dos veces la misma materia en el mismo día y horario
    (ni crearla duplicada, ni editar una mesa para que choque con otra ya
    existente); en un horario o día distinto sí se permite.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=carrera, anio=1)
        cls.preceptor = crear_usuario('prec_altamesa@test.com', 'Preceptor', 'Preceptora', 70)

    def setUp(self):
        self.client.force_login(self.preceptor)
        # Sin segundos/microsegundos: es la precisión real que entrega el
        # input datetime-local del form (ver self.datos más abajo).
        self.llamado = (timezone.now() + timedelta(days=10)).replace(second=0, microsecond=0)
        self.mesa = MesaFinal.objects.create(materia=self.materia, llamado=self.llamado)

    def datos(self, llamado):
        return {
            'materia': self.materia.id, 'llamado': llamado.strftime('%Y-%m-%dT%H:%M'),
            'aula': '', 'sede': '',
        }

    def test_no_permite_crear_una_mesa_duplicada(self):
        respuesta = self.client.post('/altaMesa/', self.datos(self.llamado))
        self.assertEqual(respuesta.status_code, 200)  # vuelve a la misma pantalla, no redirige
        self.assertEqual(MesaFinal.objects.filter(materia=self.materia, llamado=self.llamado).count(), 1)

    def test_permite_crear_la_misma_materia_en_otro_horario(self):
        otro_horario = self.llamado.replace(hour=(self.llamado.hour + 3) % 24)
        respuesta = self.client.post('/altaMesa/', self.datos(otro_horario))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(MesaFinal.objects.filter(materia=self.materia).count(), 2)

    def test_permite_crear_la_misma_materia_otro_dia(self):
        otro_dia = self.llamado + timedelta(days=1)
        respuesta = self.client.post('/altaMesa/', self.datos(otro_dia))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(MesaFinal.objects.filter(materia=self.materia).count(), 2)

    def test_no_permite_editar_una_mesa_para_que_choque_con_otra(self):
        otra = MesaFinal.objects.create(materia=self.materia, llamado=self.llamado + timedelta(days=1))
        respuesta = self.client.post(f'/edit_mesa/{otra.id}', self.datos(self.llamado))
        otra.refresh_from_db()
        self.assertNotEqual(otra.llamado, self.llamado)


class ListaMateriasUserViewTest(TestCase):
    """
    lista_materias_user (/inscripcionMateriaEst/): tabla con búsqueda, filtro
    de carrera y el panel de correlativas pendientes del rediseño.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1, inscripcionAbierta=True)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2, inscripcionAbierta=True)
        MateriaCorrelativa.objects.create(materia=cls.segundo, materia_correlativa=cls.primero)
        cls.alumno = crear_usuario('alu_lista_mat@test.com', 'Estudiante', 'Alumno', 95)
        cls.alumno.carrera.add(cls.carrera)  # bloque de ingresante: primero queda EN_CURSO

    def test_la_pagina_renderiza_sin_errores(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get('/inscripcionMateriaEst/')
        self.assertEqual(respuesta.status_code, 200)

    def test_informa_las_correlativas_que_faltan_en_el_panel(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get('/inscripcionMateriaEst/')
        self.assertIn('bloqueadas_por_correlativas', respuesta.context)
        materias_bloqueadas = [i['materia'] for i in respuesta.context['bloqueadas_por_correlativas']]
        self.assertIn(self.segundo, materias_bloqueadas)
        self.assertContains(respuesta, 'Correlativas pendientes')
        self.assertContains(respuesta, 'Programación I')

    def test_la_carrera_del_alumno_aparece_como_opcion_del_filtro(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get('/inscripcionMateriaEst/')
        self.assertContains(respuesta, 'Tecnicatura')


class InscripcionMateriaEstTest(TestCase):
    """
    inscripcionMateriaEst (/inscribirse_materia/<id>/<modalidad>): tiene que
    exigir POST. Antes mutaba en GET, disparable con un simple link o <img>
    de un sitio externo (CSRF) sin que el alumno lo pidiera.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=carrera, anio=1, inscripcionAbierta=True)
        cls.alumno = crear_usuario('alu_insc@test.com', 'Estudiante', 'Alumno', 90)
        cls.alumno.carrera.add(carrera)

    def setUp(self):
        self.client.force_login(self.alumno)
        self.url = f'/inscribirse_materia/{self.materia.id}/Regular'

    def test_get_no_inscribe(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 405)
        # anio=1 autoinscribe por la señal de ingresante en bloque (ver
        # correlativas.es_ingresante); lo que importa acá es que el GET no
        # haya sido lo que la creó, sino que no haya pisado la modalidad.
        self.assertIsNone(usuarios_materia.objects.get(usuario=self.alumno, materia=self.materia).modalidad)

    def test_post_inscribe(self):
        respuesta = self.client.post(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(usuarios_materia.objects.filter(usuario=self.alumno, materia=self.materia).exists())


class InscribirFinalReinscripcionTest(TestCase):
    """
    inscribir_final (vista admin): un resultado ya cargado (ausente o nota
    desaprobada) no debe bloquear para siempre una nueva inscripción, solo
    mientras haya un tope de oportunidades disponible. Antes, cualquier
    InscripcionFinal histórica bloqueaba la materia de por vida.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        cls.preceptor = crear_usuario('prec_reinsc@test.com', 'Preceptor', 'Preceptora', 80)
        cls.alumno = crear_usuario('alu_reinsc@test.com', 'Estudiante', 'Alumno', 81)
        cls.alumno.carrera.add(cls.carrera)

    def mesa_abierta(self, dias=5):
        return MesaFinal.objects.create(
            materia=self.materia, llamado=timezone.now() + timedelta(days=dias), inscripcionAbierta=True)

    def setUp(self):
        self.client.force_login(self.preceptor)
        usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=8)

    def test_con_un_intento_desaprobado_puede_anotarse_de_nuevo(self):
        mesa_vieja = self.mesa_abierta()
        InscripcionFinal.objects.create(usuario=self.alumno, llamado=mesa_vieja, aprobada=False, nota=2)
        mesa_nueva = self.mesa_abierta()

        respuesta = self.client.post('/inscribir_final/', {'usuario': self.alumno.id, 'llamado': mesa_nueva.id}).json()

        self.assertEqual(respuesta['status'], 'success')
        self.assertTrue(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=mesa_nueva).exists())

    def test_con_inscripcion_pendiente_no_puede_anotarse_a_otra_mesa(self):
        mesa_pendiente = self.mesa_abierta()
        InscripcionFinal.objects.create(usuario=self.alumno, llamado=mesa_pendiente)  # sin resultado todavía
        mesa_nueva = self.mesa_abierta()

        respuesta = self.client.post('/inscribir_final/', {'usuario': self.alumno.id, 'llamado': mesa_nueva.id}).json()

        self.assertEqual(respuesta['status'], 'error')
        self.assertFalse(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=mesa_nueva).exists())

    def test_con_tres_intentos_agotados_no_puede_anotarse(self):
        for _ in range(3):
            mesa_vieja = self.mesa_abierta()
            InscripcionFinal.objects.create(usuario=self.alumno, llamado=mesa_vieja, aprobada=False, nota=2)
        mesa_nueva = self.mesa_abierta()

        respuesta = self.client.post('/inscribir_final/', {'usuario': self.alumno.id, 'llamado': mesa_nueva.id}).json()

        self.assertEqual(respuesta['status'], 'error')
        self.assertIn('oportunidades', respuesta['message'])
        self.assertFalse(InscripcionFinal.objects.filter(usuario=self.alumno, llamado=mesa_nueva).exists())


class CargarNotaFinalTest(TestCase):
    """
    cargar_nota_final: el preceptor transcribe el resultado del acta en
    papel (nota o ausente) y los datos de cierre de la mesa (número de
    acta, folio). Es la pieza que cierra el circuito de Inscripción a
    Mesas de Finales del Sprint 3.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=carrera, anio=1)
        cls.preceptor = crear_usuario('prec_nota@test.com', 'Preceptor', 'Preceptora', 70)
        cls.estudiante = crear_usuario('est_nota@test.com', 'Estudiante', 'Estudiante Nota', 71)

    def setUp(self):
        self.mesa = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() - timedelta(days=1))
        self.usuario_materia = usuarios_materia.objects.create(usuario=self.estudiante, materia=self.materia)
        self.inscripcion = InscripcionFinal.objects.create(usuario=self.estudiante, llamado=self.mesa, aprobada=None)
        self.url = f'/cargar_nota_final/{self.inscripcion.id}/'
        self.client.force_login(self.preceptor)

    def test_carga_nota_actualiza_inscripcion_y_usuarios_materia(self):
        self.client.post(self.url, {'nota_final': '7'})
        self.inscripcion.refresh_from_db()
        self.usuario_materia.refresh_from_db()
        self.assertEqual(self.inscripcion.nota, 7)
        self.assertTrue(self.inscripcion.aprobada)
        self.assertFalse(self.inscripcion.ausente)
        self.assertEqual(self.usuario_materia.nota_final, 7)

    def test_marca_ausente_sin_nota_y_no_toca_usuarios_materia(self):
        usuarios_materia.objects.filter(pk=self.usuario_materia.pk).update(nota_final=3)
        self.client.post(self.url, {'ausente': 'on'})
        self.inscripcion.refresh_from_db()
        self.usuario_materia.refresh_from_db()
        self.assertTrue(self.inscripcion.ausente)
        self.assertIsNone(self.inscripcion.nota)
        self.assertFalse(self.inscripcion.aprobada)
        self.assertEqual(self.usuario_materia.nota_final, 3)  # sin cambios

    def test_no_permite_nota_y_ausente_juntos(self):
        respuesta = self.client.post(self.url, {'nota_final': '7', 'ausente': 'on'})
        self.assertEqual(respuesta.status_code, 200)  # vuelve a mostrar el form con error
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.nota)
        self.assertFalse(self.inscripcion.ausente)

    def test_exige_nota_o_ausente(self):
        respuesta = self.client.post(self.url, {})
        self.assertEqual(respuesta.status_code, 200)
        self.inscripcion.refresh_from_db()
        self.assertIsNone(self.inscripcion.nota)

    def test_guarda_numero_de_acta_y_folio_en_la_mesa(self):
        self.client.post(self.url, {'nota_final': '7', 'numero_acta': '123', 'folio': '45'})
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.numero_acta, '123')
        self.assertEqual(self.mesa.folio, '45')

    def test_estudiante_no_puede_cargar_su_propia_nota(self):
        self.client.force_login(self.estudiante)
        respuesta = self.client.post(self.url, {'nota_final': '10'})
        self.assertEqual(respuesta.status_code, 403)


class ApiListaUsuariosTest(TestCase):
    """api_lista_usuarios: búsqueda por nombre (sin tildes), DNI o email."""

    @classmethod
    def setUpTestData(cls):
        cls.url = '/api/usuarios/'
        cls.directivo = crear_usuario('dir_busq@test.com', 'Directivo', 'Directiva Busqueda', 70)
        cls.estudiante = crear_usuario('est_busq@test.com', 'Estudiante', 'Estudiante Uno', 71)

    def test_solo_personal_administrativo_accede(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_busqueda_por_nombre_ignora_tildes(self):
        crear_usuario('maria@test.com', 'Estudiante', 'María José', 72)
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url, {'q': 'maria jose'}).json()
        self.assertEqual(datos['count'], 1)
        self.assertEqual(datos['results'][0]['nombre_completo'], 'María José')

    def test_busqueda_por_dni(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url, {'q': '71'}).json()
        dnis = {r['dni'] for r in datos['results']}
        self.assertIn('71', dnis)

    def test_busqueda_por_email(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url, {'q': 'est_busq'}).json()
        self.assertEqual(datos['count'], 1)
        self.assertEqual(datos['results'][0]['email'], 'est_busq@test.com')

    def test_sin_busqueda_trae_todos_paginado(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url).json()
        self.assertEqual(datos['count'], Usuario.objects.count())

    def test_busqueda_sin_coincidencias(self):
        self.client.force_login(self.directivo)
        datos = self.client.get(self.url, {'q': 'zzzNoExiste'}).json()
        self.assertEqual(datos['count'], 0)


class EditUserCambioDeRolTest(TestCase):
    """
    El Directivo puede cambiar el rol de un usuario sin tocar sus datos
    personales, incluso si a ese usuario le faltan teléfonos u otros datos
    opcionales (antes el form se los exigía igual y bloqueaba el cambio).
    El DNI es el identificador de login: el form lo ignora pase lo que
    pase en el POST (ver profile_students_form, campo disabled=True).
    """

    @classmethod
    def setUpTestData(cls):
        cls.directivo = crear_usuario('dir_rol@test.com', 'Directivo', 'Directiva', 80)
        cls.profesor = crear_usuario('prof_rol@test.com', 'Profesor', 'Profesor Incompleto', 81)

    def datos_formulario(self, usuario, **overrides):
        datos = {
            'username': usuario.username, 'nombre_completo': usuario.nombre_completo,
            'fecha_nac': '', 'dni': usuario.dni, 'direccion': '', 'localidad': '', 'ciudad': '',
            'nacionalidad': '', 'telefono_1': '', 'telefono_2': '', 'estado_civil': '', 'sexo': '',
        }
        datos.update(overrides)
        return datos

    def test_directivo_cambia_el_rol_sin_tocar_datos_personales(self):
        self.client.force_login(self.directivo)
        response = self.client.post(
            f'/edit_user/{self.profesor.id}',
            self.datos_formulario(self.profesor, rol='Preceptor'),
        )
        self.assertEqual(response.status_code, 302)
        self.profesor.refresh_from_db()
        self.assertEqual(self.profesor.rol, 'Preceptor')
        self.assertEqual(self.profesor.nombre_completo, 'Profesor Incompleto')
        self.assertEqual(self.profesor.dni, '81')

    def test_el_dni_no_se_puede_modificar_desde_el_form(self):
        """Aunque el POST mande otro DNI, el campo disabled lo ignora."""
        self.client.force_login(self.directivo)
        self.client.post(
            f'/edit_user/{self.profesor.id}',
            self.datos_formulario(self.profesor, dni='99999999'),
        )
        self.profesor.refresh_from_db()
        self.assertEqual(self.profesor.dni, '81')

    def test_secretario_tambien_puede_cambiar_el_rol(self):
        """Secretario comparte el resto de la matriz con Directivo; esto ya no era la excepción."""
        secretario = crear_usuario('sec_rol@test.com', 'Secretario', 'Secretaria', 82)
        self.client.force_login(secretario)
        response = self.client.post(
            f'/edit_user/{self.profesor.id}',
            self.datos_formulario(self.profesor, rol='Preceptor'),
        )
        self.assertEqual(response.status_code, 302)
        self.profesor.refresh_from_db()
        self.assertEqual(self.profesor.rol, 'Preceptor')

    def test_profesor_no_puede_cambiar_roles(self):
        otro_profesor = crear_usuario('prof_otro@test.com', 'Profesor', 'Otro Profesor', 83)
        self.client.force_login(otro_profesor)
        self.client.post(
            f'/edit_user/{self.profesor.id}',
            self.datos_formulario(self.profesor, rol='Directivo'),
        )
        self.profesor.refresh_from_db()
        self.assertEqual(self.profesor.rol, 'Profesor')


class BlanquearPasswordTest(TestCase):
    """Directivo y Secretario pueden resetear contraseñas; nadie más."""

    @classmethod
    def setUpTestData(cls):
        cls.directivo = crear_usuario('dir_bp@test.com', 'Directivo', 'Directiva', 90)
        cls.secretario = crear_usuario('sec_bp@test.com', 'Secretario', 'Secretaria', 91)
        cls.preceptor = crear_usuario('prec_bp@test.com', 'Preceptor', 'Preceptora', 92)
        cls.alumno = crear_usuario('alu_bp@test.com', 'Estudiante', 'Alumno', 93)
        cls.alumno.set_password('vieja-clave')
        cls.alumno.first_login = False
        cls.alumno.save()

    def test_directivo_puede_blanquear(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/blanquear_password/{self.alumno.id}/')
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.first_login)

    def test_la_contrasena_nueva_se_muestra_en_la_misma_pantalla(self):
        """No redirige: la contraseña generada se ve ahí mismo, una sola vez."""
        self.client.force_login(self.directivo)
        response = self.client.post(f'/blanquear_password/{self.alumno.id}/')
        self.assertEqual(response.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.check_password(response.context['password_nueva']))
        self.assertContains(response, response.context['password_nueva'])

    def test_secretario_puede_blanquear(self):
        self.client.force_login(self.secretario)
        self.client.post(f'/blanquear_password/{self.alumno.id}/')
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.first_login)

    def test_preceptor_no_puede_blanquear(self):
        self.client.force_login(self.preceptor)
        response = self.client.post(f'/blanquear_password/{self.alumno.id}/')
        self.assertEqual(response.status_code, 403)
        self.alumno.refresh_from_db()
        self.assertFalse(self.alumno.first_login)


class ObtenerContextoReporteTest(TestCase):
    """
    obtener_contexto_reporte usaba una lista de materias y un nombre de
    carrera hardcodeados (de una tecnicatura en particular): cualquier
    estudiante de otra carrera recibía una constancia con materias ajenas.
    Ahora arma todo a partir de la carrera real del alumno.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(
            nombre_carrera='Tecnicatura Superior en Enfermería', num_resolucion='RES-006/2023')
        cls.materia1 = Materia.objects.create(
            nombre_materia='Fundamentos del Cuidado', carrera=cls.carrera, anio=1)
        cls.materia2 = Materia.objects.create(
            nombre_materia='Farmacología en Enfermería', carrera=cls.carrera, anio=2)
        # Materia de OTRA carrera: no debe aparecer en el reporte de este alumno.
        otra_carrera = Carrera.objects.create(nombre_carrera='Análisis de sistemas')
        Materia.objects.create(nombre_materia='Álgebra', carrera=otra_carrera, anio=1)

        cls.alumno = crear_usuario('rep_enf@test.com', 'Estudiante', 'Alumno Enfermeria', 95)
        cls.alumno.carrera.add(cls.carrera)

    def test_usa_la_carrera_real_del_alumno_no_una_hardcodeada(self):
        from inscripcionFinales.views import obtener_contexto_reporte
        ctx = obtener_contexto_reporte(self.alumno)
        self.assertEqual(ctx['nombre_carrera'], 'Tecnicatura Superior en Enfermería')
        self.assertEqual(ctx['resolucion_carrera'], 'RES-006/2023')

    def test_solo_trae_materias_de_la_carrera_del_alumno(self):
        from inscripcionFinales.views import obtener_contexto_reporte
        ctx = obtener_contexto_reporte(self.alumno)
        nombres = {m['nombre'] for materias in ctx['materias_por_anio'].values() for m in materias}
        self.assertEqual(nombres, {'Fundamentos del Cuidado', 'Farmacología en Enfermería'})
        self.assertEqual(ctx['total_materias'], 2)

    def test_final_aprobado_cuenta_para_el_porcentaje(self):
        from inscripcionFinales.views import obtener_contexto_reporte
        usuarios_materia.objects.filter(usuario=self.alumno, materia=self.materia1).update(
            nota_cursada=8, nota_final=7, estado=EstadoCursada.APROBADO)
        ctx = obtener_contexto_reporte(self.alumno)
        self.assertEqual(ctx['materias_aprobadas'], 1)
        self.assertEqual(ctx['porcentaje_aprobadas'], 50.0)


class CargarUsuariosConNotaTest(TestCase):
    """
    La carga masiva de usuarios (CSV) también puede cargar la nota de una
    materia en la misma fila: si el usuario es nuevo, se crea y se le carga;
    si ya existe, no se duplica pero igual se le carga la nota (y la carrera,
    si no la tenía) — así no hace falta un archivo aparte para eso.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.directivo = crear_usuario('dir_csv@test.com', 'Directivo', 'Directiva', 110)

    def csv_file(self, contenido):
        return SimpleUploadedFile('usuarios.csv', contenido.encode('utf-8'), content_type='text/csv')

    def test_usuario_nuevo_se_crea_y_queda_con_la_nota(self):
        self.client.force_login(self.directivo)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Carrera,Materia,Nota de cursada\n"
            "nuevo@test.com,Alumno Nuevo,777,Tecnicatura,Programación I,9\n"
        )
        self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        nuevo = Usuario.objects.get(dni=777)
        self.assertIn(self.carrera, nuevo.carrera.all())
        inscripcion = usuarios_materia.objects.get(usuario=nuevo, materia=self.materia)
        self.assertEqual(inscripcion.nota_cursada, 9)
        self.assertEqual(inscripcion.estado, EstadoCursada.REGULAR)

    def test_usuario_existente_no_se_duplica_pero_se_le_carga_la_nota(self):
        alumno = crear_usuario('existe@test.com', 'Estudiante', 'Alumno Existente', 555)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia)

        self.client.force_login(self.directivo)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Materia,Nota de cursada\n"
            "existe@test.com,Alumno Existente,555,Programación I,6\n"
        )
        self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        self.assertEqual(Usuario.objects.filter(dni=555).count(), 1)
        inscripcion = usuarios_materia.objects.get(usuario=alumno, materia=self.materia)
        self.assertEqual(inscripcion.nota_cursada, 6)

    def test_fila_sin_columna_materia_no_toca_notas(self):
        """Comportamiento de siempre: si no hay columna Materia, la carga es solo de datos personales."""
        self.client.force_login(self.directivo)
        contenido = "Correo electrónico,Nombre estudiante,Documento estudiante\nsinnota@test.com,Sin Nota,888\n"
        self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        nuevo = Usuario.objects.get(dni=888)
        self.assertFalse(usuarios_materia.objects.filter(usuario=nuevo).exists())

    def test_materia_inexistente_queda_como_error_sin_romper_la_creacion(self):
        self.client.force_login(self.directivo)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Materia,Nota de cursada\n"
            "otro@test.com,Otro Alumno,999,Materia Que No Existe,8\n"
        )
        response = self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        self.assertTrue(Usuario.objects.filter(dni=999).exists())
        self.assertIn('Materia no encontrada', response.content.decode())


    def test_rol_en_mayusculas_se_guarda_en_su_forma_canonica(self):
        self.client.force_login(self.directivo)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Rol\n"
            "prece@test.com,Preceptora Nueva,4321,PRECEPTOR\n"
            "secre@test.com,Secretario Nuevo,4322,secretario\n"
        )
        self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        self.assertEqual(Usuario.objects.get(dni=4321).rol, 'Preceptor')
        self.assertEqual(Usuario.objects.get(dni=4322).rol, 'Secretario')

    def test_rol_que_no_existe_en_el_sistema_se_rechaza(self):
        # Antes se aceptaba 'Bibliotecario': la cuenta quedaba sin ningún permiso.
        self.client.force_login(self.directivo)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Rol\n"
            "biblio@test.com,Bibliotecaria,4323,Bibliotecario\n"
        )
        response = self.client.post('/cargaMasivaEstudiantes/', {'csv_file': self.csv_file(contenido)})

        self.assertFalse(Usuario.objects.filter(dni=4323).exists())
        self.assertIn('Rol inválido', response.content.decode())


class RolesCanonicosMigracionTest(TestCase):
    """La migración 0022 lleva cada rol a la forma que usa CAPACIDADES_POR_ROL (P-12)."""

    def test_normaliza_mayusculas_y_deja_lo_desconocido(self):
        from importlib import import_module
        from django.apps import apps as apps_actuales

        prece = crear_usuario('p@test.com', 'PRECEPTOR', 'Preceptora', 4401)
        prof = crear_usuario('q@test.com', 'profesor', 'Profesor', 4402)
        raro = crear_usuario('r@test.com', 'Otro', 'Sin Rol', 4403)

        migracion = import_module('inscripcionFinales.migrations.0022_roles_canonicos')
        migracion.normalizar_roles(apps_actuales, None)

        prece.refresh_from_db()
        prof.refresh_from_db()
        raro.refresh_from_db()
        self.assertEqual(prece.rol, 'Preceptor')
        self.assertTrue(prece.puede_gestionar_mesas())
        self.assertEqual(prof.rol, 'Profesor')
        self.assertEqual(raro.rol, 'Otro')

class ConstanciaPdfTest(TestCase):
    """
    La constancia se genera dentro del sistema (#130, SEC-08). Antes se mandaba
    el HTML con nombre, DNI y notas a un servicio externo; como views.py nunca
    importó requests, además la descarga respondía siempre 500.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura en Enfermería', num_resolucion='RES-1/2024')
        Materia.objects.create(nombre_materia='Anatomía & Fisiología <I>', carrera=carrera, anio=1)
        Materia.objects.create(nombre_materia='Farmacología', carrera=carrera, anio=2)
        # Caracteres que el PDF interpreta como marcado: tienen que llegar escapados.
        cls.alumno = crear_usuario('pdf@test.com', 'Estudiante', 'José <Pérez> & Cía', 70)
        cls.alumno.carrera.add(carrera)
        cls.otro = crear_usuario('pdf2@test.com', 'Estudiante', 'Otro Alumno', 71)
        cls.url = f'/reporte/{cls.alumno.id}'

    def test_el_alumno_descarga_su_constancia_en_pdf(self):
        self.client.force_login(self.alumno)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))
        self.assertEqual(respuesta['Content-Disposition'], 'attachment; filename="constancia_jose_perez_cia.pdf"')

    def test_no_hace_pedidos_a_servicios_externos(self):
        from unittest import mock
        import socket
        self.client.force_login(self.alumno)
        with mock.patch.object(socket.socket, 'connect', side_effect=AssertionError('conexión de red')):
            respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)

    def test_otro_estudiante_no_puede_descargarla(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_si_falla_la_generacion_queda_en_el_log(self):
        from unittest import mock
        self.client.force_login(self.alumno)
        with mock.patch('inscripcionFinales.views.generar_constancia_pdf', side_effect=ValueError('roto')), \
                self.assertLogs('inscripcionFinales.views', level='ERROR') as logs:
            respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 500)
        self.assertIn('No se pudo generar la constancia', logs.output[0])


class FirstLoginPasswordChangeViewTest(TestCase):
    """
    /change_password_first/ no pedía login (SEC-10): un anónimo que la
    visitaba podía llegar a get_form_kwargs() con request.user = AnonymousUser,
    que no tiene los métodos que SetPasswordForm necesita.
    """

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario('primerlogin@test.com', 'Estudiante', 'Alumno', 90)

    def test_anonimo_no_accede(self):
        respuesta = self.client.get('/change_password_first/')
        self.assertNotEqual(respuesta.status_code, 200)

    def test_usuario_logueado_si_accede(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get('/change_password_first/')
        self.assertEqual(respuesta.status_code, 200)


class LoginThrottlingTest(TestCase):
    """
    django-axes: bloquea el login tras AXES_FAILURE_LIMIT intentos fallidos
    seguidos con el mismo usuario (SEC-04 de la auditoría de seguridad).
    """

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario('axes@test.com', 'Estudiante', 'Alumno Axes', 70)
        cls.usuario.set_password('contraseña-correcta')
        cls.usuario.save()

    def _intentar(self, password):
        return self.client.post('/accounts/login/', {'username': '70', 'password': password})

    def test_intentos_fallidos_por_debajo_del_limite_no_bloquean(self):
        from django.conf import settings
        for _ in range(settings.AXES_FAILURE_LIMIT - 1):
            self._intentar('mal')
        respuesta = self._intentar('contraseña-correcta')
        self.assertIn('_auth_user_id', self.client.session)

    def test_supera_el_limite_bloquea_incluso_con_la_contraseña_correcta(self):
        from django.conf import settings
        for _ in range(settings.AXES_FAILURE_LIMIT):
            self._intentar('mal')
        respuesta = self._intentar('contraseña-correcta')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(respuesta, 'Demasiados intentos', status_code=429)

    def test_bloqueo_es_por_usuario_no_por_ip(self):
        """Otro usuario, misma IP (mismo test client): no debería verse afectado."""
        from django.conf import settings
        otro = crear_usuario('axes_otro@test.com', 'Estudiante', 'Otro Alumno', 71)
        otro.set_password('otra-contraseña')
        otro.save()

        for _ in range(settings.AXES_FAILURE_LIMIT):
            self._intentar('mal')  # agota el límite de axes@test.com

        respuesta = self.client.post('/accounts/login/', {'username': '71', 'password': 'otra-contraseña'})
        self.assertIn('_auth_user_id', self.client.session)


class LogoutTest(TestCase):
    """Desde Django 5.0, LogoutView solo acepta POST (#128)."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario('logout@test.com', 'Estudiante', 'Alumno Logout', 60)

    def test_post_cierra_la_sesion_y_avisa(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post('/accounts/logout/', follow=True)
        self.assertRedirects(respuesta, '/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        mensajes = [str(m) for m in respuesta.context['messages']] if respuesta.context else []
        self.assertIn('Su sesión se ha cerrado correctamente.', mensajes)

    def test_get_no_cierra_la_sesion(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get('/accounts/logout/')
        self.assertEqual(respuesta.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)


class RecuperarPasswordPorDniTest(TestCase):
    """
    El login es por DNI, no por email (ver CustomLoginView), así que acá
    también se pide el DNI. La respuesta tiene que ser idéntica exista o no
    la cuenta, y tenga o no email cargado, para no revelar esos datos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.con_email = crear_usuario('recuperar_con_mail@test.com', 'Estudiante', 'Con Email', 70)
        cls.sin_email = Usuario.objects.create(
            username='recuperar_sin_mail', nombre_completo='Sin Email', rol='Estudiante', dni=71,
        )

    def test_get_muestra_el_formulario_pidiendo_dni(self):
        respuesta = self.client.get('/recuperar_pass/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'DNI')

    def test_dni_con_email_manda_el_correo_de_reseteo(self):
        respuesta = self.client.post('/recuperar_pass/', {'dni': '70'})
        self.assertRedirects(respuesta, '/password_reset/done/')
        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertEqual(enviado.to, ['recuperar_con_mail@test.com'])
        self.assertEqual(enviado.subject, 'Recuperar tu contraseña - SIMEF')
        self.assertIn('Con Email', enviado.body)  # nombre_completo en el contexto del mail
        # multipart/alternative: versión HTML además de la de texto plano
        self.assertEqual(len(enviado.alternatives), 1)
        html, mimetype = enviado.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('Elegir nueva contraseña', html)

    def test_dni_sin_email_no_manda_nada_pero_misma_respuesta(self):
        respuesta = self.client.post('/recuperar_pass/', {'dni': '71'})
        self.assertRedirects(respuesta, '/password_reset/done/')
        self.assertEqual(len(mail.outbox), 0)

    def test_dni_inexistente_no_manda_nada_pero_misma_respuesta(self):
        respuesta = self.client.post('/recuperar_pass/', {'dni': '000000'})
        self.assertRedirects(respuesta, '/password_reset/done/')
        self.assertEqual(len(mail.outbox), 0)

    def test_el_link_del_correo_usa_el_token_de_django(self):
        self.client.post('/recuperar_pass/', {'dni': '70'})
        cuerpo = mail.outbox[0].body
        self.assertIn('/reset/', cuerpo)
