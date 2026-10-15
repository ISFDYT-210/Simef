"""
Tests de la lógica que vive en los modelos.

Cubre la señal de inscripción automática a primer año y la ventana real de
inscripción de una mesa (inscripcion_vigente), que decide qué ve el listado.

Correr con:
    python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
"""
from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone

from inscripcionFinales.models import (
    BLOQUEO_LOGIN_MINUTOS_BASE, BLOQUEO_LOGIN_MINUTOS_TOPE, Carrera, Materia, MesaFinal,
    Usuario, duracion_bloqueo_login, usuarios_materia,
)


class InscripcionAutomaticaPrimerAnioTest(TestCase):
    """
    Al asignarle una carrera a un estudiante se lo inscribe en todas las
    materias de primer año de esa carrera (cursada en bloque).
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.otra_carrera = Carrera.objects.create(nombre_carrera='Profesorado')

        cls.primero_a = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.primero_b = Materia.objects.create(
            nombre_materia='Matemática I', carrera=cls.carrera, anio=1)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        cls.ajena = Materia.objects.create(
            nombre_materia='Didáctica', carrera=cls.otra_carrera, anio=1)

    def crear_estudiante(self, dni):
        return Usuario.objects.create(
            email=f'e{dni}@test.com', username=f'e{dni}',
            nombre_completo=f'Estudiante {dni}', rol='Estudiante', dni=dni,
        )

    def materias_de(self, usuario):
        return set(
            usuarios_materia.objects
            .filter(usuario=usuario)
            .values_list('materia__nombre_materia', flat=True)
        )

    def test_inscribe_solo_las_materias_de_primer_anio(self):
        estudiante = self.crear_estudiante(100)
        estudiante.carrera.add(self.carrera)

        self.assertEqual(
            self.materias_de(estudiante),
            {'Programación I', 'Matemática I'},
        )

    def test_no_inscribe_materias_de_otra_carrera(self):
        estudiante = self.crear_estudiante(101)
        estudiante.carrera.add(self.carrera)
        self.assertNotIn('Didáctica', self.materias_de(estudiante))

    def test_funciona_con_set_ademas_de_add(self):
        """El alta individual usa carrera.set(); la carga masiva usa carrera.add()."""
        estudiante = self.crear_estudiante(102)
        estudiante.carrera.set([self.carrera])
        self.assertEqual(len(self.materias_de(estudiante)), 2)

    def test_no_inscribe_a_quien_no_es_estudiante(self):
        profesor = Usuario.objects.create(
            email='p@test.com', username='p', nombre_completo='Profe',
            rol='Profesor', dni=103,
        )
        profesor.carrera.add(self.carrera)
        self.assertEqual(self.materias_de(profesor), set())

    def test_reasignar_la_carrera_no_duplica_inscripciones(self):
        estudiante = self.crear_estudiante(104)
        estudiante.carrera.add(self.carrera)
        estudiante.carrera.add(self.carrera)
        estudiante.carrera.set([self.carrera])

        self.assertEqual(usuarios_materia.objects.filter(usuario=estudiante).count(), 2)

    def test_agregar_una_segunda_carrera_suma_sin_pisar(self):
        estudiante = self.crear_estudiante(105)
        estudiante.carrera.add(self.carrera)
        estudiante.carrera.add(self.otra_carrera)

        self.assertEqual(
            self.materias_de(estudiante),
            {'Programación I', 'Matemática I', 'Didáctica'},
        )

    def test_no_pisa_una_inscripcion_previa_con_notas(self):
        """Si ya cursó la materia, la señal no puede borrarle la nota."""
        estudiante = self.crear_estudiante(106)
        usuarios_materia.objects.create(
            usuario=estudiante, materia=self.primero_a, nota_cursada=9,
        )

        estudiante.carrera.add(self.carrera)

        inscripcion = usuarios_materia.objects.get(
            usuario=estudiante, materia=self.primero_a)
        self.assertEqual(inscripcion.nota_cursada, 9)


class InscripcionVigenteTest(TestCase):
    """
    inscripcion_vigente(): abierta de verdad solo hasta el día del examen,
    aunque nadie la haya cerrado a mano.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Carrera')
        cls.materia = Materia.objects.create(
            nombre_materia='Materia', carrera=carrera, anio=1)

    def mesa(self, dias, abierta):
        return MesaFinal.objects.create(
            materia=self.materia,
            llamado=timezone.now() + timedelta(days=dias),
            inscripcionAbierta=abierta,
        )

    def test_abierta_y_a_futuro_esta_vigente(self):
        self.assertTrue(self.mesa(dias=5, abierta=True).inscripcion_vigente())

    def test_abierta_pero_ya_paso_no_esta_vigente(self):
        self.assertFalse(self.mesa(dias=-1, abierta=True).inscripcion_vigente())

    def test_cerrada_nunca_esta_vigente(self):
        self.assertFalse(self.mesa(dias=5, abierta=False).inscripcion_vigente())

    def test_el_mismo_dia_del_examen_sigue_vigente(self):
        """La ventana incluye el día del llamado."""
        mesa = MesaFinal.objects.create(
            materia=self.materia,
            llamado=timezone.now() + timedelta(minutes=1),
            inscripcionAbierta=True,
        )
        self.assertTrue(mesa.inscripcion_vigente())


class InscripcionExcepcionalVigenteTest(TestCase):
    """
    inscripcion_excepcional_vigente(): no depende de inscripcionAbierta, pero
    se corta si faltan menos de LIMITE_DIAS_EXCEPCION (2) días para el examen.
    """

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Carrera')
        cls.materia = Materia.objects.create(nombre_materia='Materia', carrera=carrera, anio=1)

    def mesa(self, dias, abierta=False):
        return MesaFinal.objects.create(
            materia=self.materia, llamado=timezone.now() + timedelta(days=dias),
            inscripcionAbierta=abierta,
        )

    def test_cerrada_pero_con_margen_permite_excepcion(self):
        self.assertTrue(self.mesa(dias=5).inscripcion_excepcional_vigente())

    def test_justo_en_el_limite_permite_excepcion(self):
        self.assertTrue(self.mesa(dias=2).inscripcion_excepcional_vigente())

    def test_a_menos_de_2_dias_no_permite_excepcion(self):
        self.assertFalse(self.mesa(dias=1).inscripcion_excepcional_vigente())

    def test_ya_paso_no_permite_excepcion(self):
        self.assertFalse(self.mesa(dias=-1).inscripcion_excepcional_vigente())


class DuracionBloqueoLoginTest(TestCase):
    """
    duracion_bloqueo_login (AXES_COOLOFF_TIME): 10 minutos el primer
    bloqueo, +10 cada vez que la MISMA cuenta se vuelve a bloquear, hasta
    un tope. Se resetea con un login exitoso (ver CustomLoginView).
    """

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create(
            email='bloqueo@test.com', username='bloqueo', nombre_completo='Bloqueo Test',
            rol='Estudiante', dni='80',
        )

    def _request(self):
        return RequestFactory().post('/accounts/login/', {'username': '80', 'password': 'x'})

    def test_primer_bloqueo_dura_el_minimo_base(self):
        duracion = duracion_bloqueo_login(self._request())
        self.assertEqual(duracion, timedelta(minutes=BLOQUEO_LOGIN_MINUTOS_BASE))
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nivel_bloqueo_login, 1)

    def test_segundo_bloqueo_de_la_misma_cuenta_duplica_la_espera(self):
        duracion_bloqueo_login(self._request())  # primer bloqueo: nivel 1
        # Simula que el primer bloqueo ya venció (episodio cerrado).
        self.usuario.refresh_from_db()
        self.usuario.bloqueado_login_hasta = timezone.now() - timedelta(seconds=1)
        self.usuario.save()

        duracion = duracion_bloqueo_login(self._request())  # segundo bloqueo: nivel 2
        self.assertEqual(duracion, timedelta(minutes=BLOQUEO_LOGIN_MINUTOS_BASE * 2))

    def test_mismo_episodio_no_escala_de_nuevo(self):
        """Mientras el bloqueo sigue vigente, reintentos no deberían subir el nivel."""
        primera = duracion_bloqueo_login(self._request())
        segunda = duracion_bloqueo_login(self._request())
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nivel_bloqueo_login, 1)
        self.assertLessEqual(segunda, primera)

    def test_no_supera_el_tope(self):
        self.usuario.nivel_bloqueo_login = 999
        self.usuario.save()
        duracion = duracion_bloqueo_login(self._request())
        self.assertEqual(duracion, timedelta(minutes=BLOQUEO_LOGIN_MINUTOS_TOPE))

    def test_cuenta_inexistente_usa_el_minimo_base(self):
        request = RequestFactory().post('/accounts/login/', {'username': '99999999', 'password': 'x'})
        self.assertEqual(duracion_bloqueo_login(request), timedelta(minutes=BLOQUEO_LOGIN_MINUTOS_BASE))
