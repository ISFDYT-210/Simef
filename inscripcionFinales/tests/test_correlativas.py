"""
Tests de inscripcionFinales/correlativas.py y de EstadoCursada.recalcular_estado.

Reglas cubiertas (ver docstring del módulo correlativas.py):
- Primer año en bloque: el ingresante no evalúa correlativas.
- Para cursar: alcanza con la cursada aprobada de la correlativa.
- Para rendir: hace falta el final aprobado de la correlativa.
- recalcular_estado() deriva el estado de las notas y no pisa estados manuales.

Correr con:
    python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from inscripcionFinales import correlativas
from inscripcionFinales.models import (
    Carrera, EstadoCursada, InscripcionFinal, Materia, MateriaCorrelativa,
    MesaFinal, Usuario, usuarios_materia,
)


class EstudianteTestMixin:
    def estudiante(self, dni):
        return Usuario.objects.create(
            email=f'c{dni}@test.com', username=f'c{dni}',
            nombre_completo=f'Estudiante {dni}', rol='Estudiante', dni=dni,
        )


class RecalcularEstadoTest(TestCase, EstudianteTestMixin):

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)

    def test_sin_notas_queda_en_curso(self):
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(1), materia=self.materia)
        self.assertEqual(inscripcion.estado, EstadoCursada.EN_CURSO)

    def test_cursada_aprobada_pasa_a_regular_y_fija_fecha(self):
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(2), materia=self.materia, nota_cursada=6)
        self.assertEqual(inscripcion.estado, EstadoCursada.REGULAR)
        self.assertIsNotNone(inscripcion.fecha_regularidad)

    def test_nota_cursada_siete_o_mas_promociona(self):
        """Regla confirmada con el instituto: >=7 promociona, aprueba toda la materia sin rendir final."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(70), materia=self.materia, nota_cursada=7)
        self.assertEqual(inscripcion.estado, EstadoCursada.PROMOCIONADO)

    def test_nota_cursada_seis_no_promociona(self):
        """Justo debajo del corte de promoción: cursada aprobada, pero sigue necesitando rendir final."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(71), materia=self.materia, nota_cursada=6.99)
        self.assertEqual(inscripcion.estado, EstadoCursada.REGULAR)

    def test_promocionado_cuenta_como_final_aprobado_para_correlativas(self):
        """PROMOCIONADO no necesita rendir el final: ya habilita a cursar/rendir la materia siguiente."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(72), materia=self.materia, nota_cursada=8)
        self.assertTrue(correlativas.tiene_final_aprobado(inscripcion))

    def test_promocionado_no_puede_volver_a_rendir(self):
        alumno = self.estudiante(73)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=8)
        puede, motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertFalse(puede)
        self.assertIn('ya tiene el final aprobado', motivo)

    def test_cursada_desaprobada_pasa_a_recursa(self):
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(3), materia=self.materia, nota_cursada=2)
        self.assertEqual(inscripcion.estado, EstadoCursada.RECURSA)

    def test_final_aprobado_pasa_a_aprobado(self):
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(4), materia=self.materia, nota_cursada=6, nota_final=7)
        self.assertEqual(inscripcion.estado, EstadoCursada.APROBADO)

    def test_libre_sin_cursada_no_pasa_a_recursa(self):
        """Libre no tiene nota de cursada; no hay que degradarlo a RECURSA."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(5), materia=self.materia, modalidad='Libre')
        self.assertEqual(inscripcion.estado, EstadoCursada.EN_CURSO)

    def test_promocionado_no_se_pisa_al_guardar_otra_nota(self):
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(6), materia=self.materia, estado=EstadoCursada.PROMOCIONADO)
        inscripcion.nota_cursada = 2
        inscripcion.save()
        self.assertEqual(inscripcion.estado, EstadoCursada.PROMOCIONADO)

    def test_ciclo_actual_desde_se_fija_al_crear(self):
        inscripcion = usuarios_materia.objects.create(usuario=self.estudiante(7), materia=self.materia)
        self.assertIsNotNone(inscripcion.ciclo_actual_desde)

    def test_recursar_renueva_el_ciclo_actual(self):
        """Cursada desaprobada (RECURSA) y después vuelve a cursar con otra nota: eso arranca un ciclo nuevo."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(8), materia=self.materia, nota_cursada=2)
        self.assertEqual(inscripcion.estado, EstadoCursada.RECURSA)
        ciclo_original = inscripcion.ciclo_actual_desde

        inscripcion.nota_cursada = 6  # recursó y ahora sí aprobó la cursada
        inscripcion.save()

        self.assertEqual(inscripcion.estado, EstadoCursada.REGULAR)
        self.assertGreater(inscripcion.ciclo_actual_desde, ciclo_original)

    def test_guardar_sin_cambiar_nota_no_renueva_el_ciclo(self):
        """Una corrección que no cambia nota_cursada (ej. tocar otro campo) no debe resetear el ciclo."""
        inscripcion = usuarios_materia.objects.create(
            usuario=self.estudiante(9), materia=self.materia, nota_cursada=2)
        ciclo_original = inscripcion.ciclo_actual_desde

        inscripcion.turno = 'Tarde'
        inscripcion.save()

        self.assertEqual(inscripcion.ciclo_actual_desde, ciclo_original)


class EsIngresanteTest(TestCase, EstudianteTestMixin):

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)

    def test_con_solo_materias_de_primero_es_ingresante(self):
        alumno = self.estudiante(10)
        usuarios_materia.objects.create(usuario=alumno, materia=self.primero)
        self.assertTrue(correlativas.es_ingresante(alumno.id, self.carrera.id))

    def test_con_una_materia_de_segundo_ya_no_es_ingresante(self):
        alumno = self.estudiante(11)
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo)
        self.assertFalse(correlativas.es_ingresante(alumno.id, self.carrera.id))


class PuedeCursarTest(TestCase, EstudianteTestMixin):
    """Regla 1 (bloque de primer año) y Regla 2 (cursada aprobada de la correlativa)."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        MateriaCorrelativa.objects.create(materia=cls.segundo, materia_correlativa=cls.primero)

    def test_ingresante_puede_cursar_materia_de_primero_sin_correlativas(self):
        """Ingresante = todavía sin ninguna inscripción; recién ahí se evalúa puede_cursar."""
        alumno = self.estudiante(20)
        puede, motivo = correlativas.puede_cursar(alumno.id, self.primero.id)
        self.assertTrue(puede)
        self.assertIsNone(motivo)

    def test_con_cursada_aprobada_de_la_correlativa_puede_cursar_aunque_no_rindio_el_final(self):
        """Regla 2: para cursar no hace falta el final de la correlativa."""
        alumno = self.estudiante(21)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=6)  # sin nota_final
        puede, motivo = correlativas.puede_cursar(alumno.id, self.segundo.id)
        self.assertTrue(puede)
        self.assertIsNone(motivo)

    def test_sin_cursada_aprobada_de_la_correlativa_no_puede_cursar(self):
        alumno = self.estudiante(22)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=2)
        puede, motivo = correlativas.puede_cursar(alumno.id, self.segundo.id)
        self.assertFalse(puede)
        self.assertIn('Programación I', motivo)

    def test_ya_inscripto_no_puede_volver_a_inscribirse(self):
        alumno = self.estudiante(23)
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo, nota_cursada=6)
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.segundo.id)
        self.assertFalse(puede)

    def test_recursa_puede_volver_a_inscribirse(self):
        """RECURSA no es una inscripción activa: el alumno puede recursar."""
        alumno = self.estudiante(24)
        usuarios_materia.objects.create(usuario=alumno, materia=self.primero, nota_cursada=6)
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo, nota_cursada=2)  # -> RECURSA
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.segundo.id)
        self.assertTrue(puede)

    def test_abandono_puede_volver_a_inscribirse(self):
        alumno = self.estudiante(25)
        usuarios_materia.objects.create(usuario=alumno, materia=self.primero, nota_cursada=6)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.segundo, estado=EstadoCursada.ABANDONO)
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.segundo.id)
        self.assertTrue(puede)


class HorarioOcupadoTest(TestCase, EstudianteTestMixin):
    """
    Superposición de horarios: no se puede cursar una materia nueva si ya se
    está cursando (EN_CURSO) otra materia el mismo día al mismo horario.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.lunes_12 = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=2,
            dia='Lunes', Horario='12:00', inscripcionAbierta=True)
        cls.tambien_lunes_12 = Materia.objects.create(
            nombre_materia='Matemática I', carrera=cls.carrera, anio=2,
            dia='Lunes', Horario='12:00', inscripcionAbierta=True)
        cls.lunes_14 = Materia.objects.create(
            nombre_materia='Historia I', carrera=cls.carrera, anio=2,
            dia='Lunes', Horario='14:00', inscripcionAbierta=True)
        cls.martes_12 = Materia.objects.create(
            nombre_materia='Física I', carrera=cls.carrera, anio=2,
            dia='Martes', Horario='12:00', inscripcionAbierta=True)

    def test_mismo_dia_y_horario_bloquea(self):
        alumno = self.estudiante(26)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12)  # EN_CURSO
        puede, motivo = correlativas.puede_cursar(alumno.id, self.tambien_lunes_12.id)
        self.assertFalse(puede)
        self.assertIn('Cursando', motivo)
        self.assertIn('Lunes', motivo)

    def test_mismo_dia_distinto_horario_no_bloquea(self):
        alumno = self.estudiante(27)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12)
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.lunes_14.id)
        self.assertTrue(puede)

    def test_mismo_horario_distinto_dia_no_bloquea(self):
        alumno = self.estudiante(28)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12)
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.martes_12.id)
        self.assertTrue(puede)

    def test_cursada_ya_regular_no_ocupa_mas_el_horario(self):
        """Ya aprobó la cursada: dejó de asistir a esas clases, no bloquea un horario nuevo."""
        alumno = self.estudiante(29)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12, nota_cursada=6)  # REGULAR
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.tambien_lunes_12.id)
        self.assertTrue(puede)

    def test_recursa_no_ocupa_el_horario(self):
        alumno = self.estudiante(30)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12, nota_cursada=2)  # RECURSA
        puede, _motivo = correlativas.puede_cursar(alumno.id, self.tambien_lunes_12.id)
        self.assertTrue(puede)

    def test_materias_con_requisitos_informa_el_motivo(self):
        alumno = self.estudiante(31)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.create(usuario=alumno, materia=self.lunes_12)
        items = {i['materia']: i for i in correlativas.materias_con_requisitos(alumno)}
        self.assertFalse(items[self.tambien_lunes_12]['disponible'])
        self.assertIn('Cursando', items[self.tambien_lunes_12]['motivo'])
        self.assertTrue(items[self.lunes_14]['disponible'])


class MateriasDisponiblesParaCursarTest(TestCase, EstudianteTestMixin):
    """Bulk usado por lista_materias_user: misma regla de recursada que puede_cursar."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1,
            inscripcionAbierta=True)

    def test_con_abandono_la_materia_vuelve_a_aparecer_como_disponible(self):
        alumno = self.estudiante(26)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.materia).update(
            estado=EstadoCursada.ABANDONO)
        disponibles = correlativas.materias_disponibles_para_cursar(alumno)
        self.assertIn(self.materia, disponibles)

    def test_con_cursada_en_curso_no_aparece_como_disponible(self):
        alumno = self.estudiante(27)
        alumno.carrera.add(self.carrera)  # la señal ya lo inscribe en bloque (EN_CURSO)
        disponibles = correlativas.materias_disponibles_para_cursar(alumno)
        self.assertNotIn(self.materia, disponibles)


class MateriaSinCorrelativaCargadaTest(TestCase, EstudianteTestMixin):
    """
    Bug real: una materia de año 2+ sin NINGUNA correlativa cargada en la
    base quedaba "disponible" para cualquiera (lista vacía -> all([]) es
    True), incluido un ingresante recién anotado que todavía no completó
    primer año. La regla ahora es: sin correlativa cargada para guiarse, no
    se adelantan materias de años superiores mientras siga en el bloque de
    primer año.
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura Superior en Enfermería')
        cls.primero = Materia.objects.create(
            nombre_materia='Fundamentos del Cuidado', carrera=cls.carrera, anio=1, inscripcionAbierta=True)
        # Sin MateriaCorrelativa configurada a propósito: así era como se
        # reprodujo el bug (ej. "Inglés" de 2do año sin correlativa cargada).
        cls.sin_correlativa = Materia.objects.create(
            nombre_materia='Inglés', carrera=cls.carrera, anio=2, inscripcionAbierta=True,
            dia='Martes', Horario='14:00')

    def test_ingresante_recien_anotado_no_ve_disponible_la_materia_de_segundo(self):
        alumno = self.estudiante(50)
        alumno.carrera.add(self.carrera)  # la señal lo inscribe en bloque, primero queda EN_CURSO
        items = {i['materia']: i for i in correlativas.materias_con_requisitos(alumno)}
        self.assertFalse(items[self.sin_correlativa]['disponible'])
        self.assertIn('primer año', items[self.sin_correlativa]['motivo'])

    def test_puede_cursar_bloquea_lo_mismo_para_un_solo_item(self):
        alumno = self.estudiante(51)
        alumno.carrera.add(self.carrera)
        puede, motivo = correlativas.puede_cursar(alumno.id, self.sin_correlativa.id)
        self.assertFalse(puede)
        self.assertIn('primer año', motivo)

    def test_una_vez_que_sale_del_bloque_de_primer_anio_si_la_ve(self):
        """Ya no es 'ingresante' (avanzó a una materia de año superior): la sin-correlativa se habilita."""
        alumno = self.estudiante(52)
        alumno.carrera.add(self.carrera)
        otra_de_segundo = Materia.objects.create(
            nombre_materia='Otra de Segundo', carrera=self.carrera, anio=2, inscripcionAbierta=True)
        usuarios_materia.objects.create(usuario=alumno, materia=otra_de_segundo)  # ya avanzó
        puede, motivo = correlativas.puede_cursar(alumno.id, self.sin_correlativa.id)
        self.assertTrue(puede)
        self.assertIsNone(motivo)


class MateriasConRequisitosTest(TestCase, EstudianteTestMixin):
    """Desglose para la UI: por qué una materia no está disponible, no solo que no lo está."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1, inscripcionAbierta=True)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2, inscripcionAbierta=True)
        MateriaCorrelativa.objects.create(materia=cls.segundo, materia_correlativa=cls.primero)

    def test_disponible_no_tiene_motivo(self):
        alumno = self.estudiante(40)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(
            nota_cursada=6, estado=EstadoCursada.REGULAR)
        items = {i['materia']: i for i in correlativas.materias_con_requisitos(alumno)}
        self.assertTrue(items[self.segundo]['disponible'])
        self.assertIsNone(items[self.segundo]['motivo'])

    def test_no_disponible_trae_el_motivo_puntual(self):
        alumno = self.estudiante(41)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.create(usuario=alumno, materia=self.primero, nota_cursada=2)  # RECURSA
        items = {i['materia']: i for i in correlativas.materias_con_requisitos(alumno)}
        self.assertFalse(items[self.segundo]['disponible'])
        self.assertIn('Programación I', items[self.segundo]['motivo'])
        self.assertEqual(items[self.segundo]['correlativas_faltantes'], [self.primero])

    def test_disponible_trae_la_lista_de_faltantes_vacia(self):
        """correlativas_faltantes siempre está presente, vacía si no bloquea nada (para el panel de la UI)."""
        alumno = self.estudiante(43)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(
            nota_cursada=6, estado=EstadoCursada.REGULAR)
        items = {i['materia']: i for i in correlativas.materias_con_requisitos(alumno)}
        self.assertEqual(items[self.segundo]['correlativas_faltantes'], [])

    def test_materia_con_cursada_activa_no_aparece_en_el_desglose(self):
        """Ya la está cursando: no es candidata a "inscribirse", no tiene sentido listarla acá."""
        alumno = self.estudiante(42)
        alumno.carrera.add(self.carrera)  # la señal la inscribe en bloque (EN_CURSO)
        materias = [i['materia'] for i in correlativas.materias_con_requisitos(alumno)]
        self.assertNotIn(self.primero, materias)

    def test_materia_ya_cursada_por_completo_no_aparece_en_el_desglose(self):
        """Ya la cursó (no la está cursando ahora): no es candidata a nada de esto, no tiene sentido listarla."""
        alumno = self.estudiante(45)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(
            nota_cursada=8, estado=EstadoCursada.APROBADO)
        materias = [i['materia'] for i in correlativas.materias_con_requisitos(alumno)]
        self.assertNotIn(self.primero, materias)


class PuedeRendirTest(TestCase, EstudianteTestMixin):
    """Regla 3: cursada aprobada de la materia + final aprobado de cada correlativa."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.segundo = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        MateriaCorrelativa.objects.create(materia=cls.segundo, materia_correlativa=cls.primero)

    def test_con_final_de_la_correlativa_aprobado_puede_rendir(self):
        alumno = self.estudiante(30)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=6, nota_final=7)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.segundo, nota_cursada=6)
        puede, motivo = correlativas.puede_rendir(alumno.id, self.segundo.id)
        self.assertTrue(puede)
        self.assertIsNone(motivo)

    def test_con_solo_cursada_aprobada_de_la_correlativa_no_puede_rendir(self):
        """Tener la cursada de la correlativa no alcanza para rendir: hace falta el final."""
        alumno = self.estudiante(31)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=6)  # sin nota_final
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.segundo, nota_cursada=6)
        puede, motivo = correlativas.puede_rendir(alumno.id, self.segundo.id)
        self.assertFalse(puede)
        self.assertIn('Programación I', motivo)

    def test_sin_cursada_propia_aprobada_no_puede_rendir(self):
        alumno = self.estudiante(32)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=6, nota_final=7)
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo)  # sin cursar
        puede, motivo = correlativas.puede_rendir(alumno.id, self.segundo.id)
        self.assertFalse(puede)

    def test_promocion_cuenta_como_final_aprobado_de_la_correlativa(self):
        alumno = self.estudiante(33)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, estado=EstadoCursada.PROMOCIONADO)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.segundo, nota_cursada=6)
        puede, _motivo = correlativas.puede_rendir(alumno.id, self.segundo.id)
        self.assertTrue(puede)

    def test_final_ya_aprobado_no_vuelve_a_rendir(self):
        alumno = self.estudiante(34)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.primero, nota_cursada=6, nota_final=7)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.segundo, nota_cursada=6, nota_final=8)
        puede, _motivo = correlativas.puede_rendir(alumno.id, self.segundo.id)
        self.assertFalse(puede)


class FinalesConRequisitosTest(TestCase, EstudianteTestMixin):
    """Desglose para la UI de finales: por qué una mesa no está disponible."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.primero = Materia.objects.create(nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.segundo = Materia.objects.create(nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        MateriaCorrelativa.objects.create(materia=cls.segundo, materia_correlativa=cls.primero)

    def mesa(self, materia, dias=5, inscripcion_abierta=True):
        return MesaFinal.objects.create(
            materia=materia, llamado=timezone.now() + timedelta(days=dias),
            inscripcionAbierta=inscripcion_abierta,
        )

    def test_no_inscripto_en_la_materia(self):
        """`segundo` (año 2) no se autoinscribe por la señal de bloque, a diferencia de `primero`."""
        alumno = self.estudiante(50)
        alumno.carrera.add(self.carrera)
        mesa = self.mesa(self.segundo)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('No estás inscripto', items[mesa]['motivo'])

    def test_sin_cursada_aprobada_no_puede_inscribirse(self):
        alumno = self.estudiante(51)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 2
        cursada.save()  # RECURSA
        mesa = self.mesa(self.primero)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('cursada aprobada', items[mesa]['motivo'])

    def test_con_cursada_regular_pero_no_promocionada_puede_rendir(self):
        """nota_cursada 4-6 (REGULAR, no promociona): cursada aprobada, el final sigue siendo obligatorio."""
        alumno = self.estudiante(57)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 5
        cursada.save()
        mesa = self.mesa(self.primero)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertTrue(items[mesa]['disponible'])
        self.assertIsNone(items[mesa]['motivo'])

    def test_correlativa_sin_final_aprobado(self):
        """primero: cursada aprobada (REGULAR, nota 6) pero sin rendir su final todavía."""
        alumno = self.estudiante(52)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 6
        cursada.save()
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo, nota_cursada=6)
        mesa = self.mesa(self.segundo)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('Programación I', items[mesa]['motivo'])

    def test_cumple_todo_queda_disponible(self):
        alumno = self.estudiante(53)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 6
        cursada.save()
        mesa = self.mesa(self.primero)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertTrue(items[mesa]['disponible'])
        self.assertIsNone(items[mesa]['motivo'])

    def test_mesa_sin_inscripcion_abierta(self):
        alumno = self.estudiante(54)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 6
        cursada.save()
        mesa = self.mesa(self.primero, inscripcion_abierta=False)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('no está abierta', items[mesa]['motivo'])

    def test_ya_inscripto_en_una_mesa_de_la_materia(self):
        alumno = self.estudiante(55)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 6
        cursada.save()
        mesa_vieja = self.mesa(self.primero, dias=2)
        InscripcionFinal.objects.create(usuario=alumno, llamado=mesa_vieja)
        mesa_nueva = self.mesa(self.primero, dias=10)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa_nueva]['disponible'])
        self.assertIn('Ya estás inscripto', items[mesa_nueva]['motivo'])

    def test_resultado_ya_cargado_no_bloquea_una_nueva_inscripcion(self):
        """
        Antes, CUALQUIER InscripcionFinal histórica (tenga o no resultado)
        bloqueaba para siempre una materia: un alumno que desaprobaba un
        final una vez nunca más podía volver a anotarse. Con resultado
        cargado (nota o ausente), si le quedan oportunidades, tiene que
        poder inscribirse a una mesa nueva.
        """
        alumno = self.estudiante(56)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.primero)
        cursada.nota_cursada = 6
        cursada.save()
        mesa_rendida = self.mesa(self.primero, dias=-2)
        InscripcionFinal.objects.create(usuario=alumno, llamado=mesa_rendida, aprobada=False, nota=2)
        mesa_nueva = self.mesa(self.primero, dias=10)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertTrue(items[mesa_nueva]['disponible'])


class OportunidadesFinalTest(TestCase, EstudianteTestMixin):
    """Tope de MAX_OPORTUNIDADES_FINAL (4) intentos de final por materia."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(nombre_materia='Programación I', carrera=cls.carrera, anio=1)

    def mesa(self, dias):
        return MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() + timedelta(days=dias))

    def test_pendiente_sin_resultado_no_consume_oportunidad(self):
        alumno = self.estudiante(60)
        um = usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        InscripcionFinal.objects.create(usuario=alumno, llamado=self.mesa(5))  # todavía sin rendir
        self.assertEqual(correlativas.intentos_consumidos(alumno.id, self.materia.id, um), 0)

    def test_ausente_consume_una_oportunidad(self):
        alumno = self.estudiante(61)
        um = usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        InscripcionFinal.objects.create(usuario=alumno, llamado=self.mesa(1), aprobada=False, ausente=True)
        self.assertEqual(correlativas.intentos_consumidos(alumno.id, self.materia.id, um), 1)

    def test_nota_desaprobada_consume_una_oportunidad(self):
        alumno = self.estudiante(62)
        um = usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        InscripcionFinal.objects.create(usuario=alumno, llamado=self.mesa(1), aprobada=False, nota=3)
        self.assertEqual(correlativas.intentos_consumidos(alumno.id, self.materia.id, um), 1)

    def test_cuarto_intento_agotado_bloquea_el_quinto(self):
        alumno = self.estudiante(63)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        for i in range(4):
            InscripcionFinal.objects.create(
                usuario=alumno, llamado=self.mesa(1 + i), aprobada=False, nota=2)
        puede, motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertFalse(puede)
        self.assertIn('4 oportunidades', motivo)

    def test_con_dos_intentos_todavia_puede_rendir(self):
        alumno = self.estudiante(64)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        for i in range(2):
            InscripcionFinal.objects.create(
                usuario=alumno, llamado=self.mesa(1 + i), aprobada=False, nota=2)
        puede, _motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertTrue(puede)

    def test_con_tres_intentos_todavia_puede_rendir(self):
        alumno = self.estudiante(67)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=6)
        for i in range(3):
            InscripcionFinal.objects.create(
                usuario=alumno, llamado=self.mesa(1 + i), aprobada=False, nota=2)
        puede, _motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertTrue(puede)

    def test_finales_con_requisitos_informa_oportunidades_agotadas(self):
        alumno = self.estudiante(65)
        alumno.carrera.add(self.carrera)
        cursada = usuarios_materia.objects.get(usuario=alumno, materia=self.materia)
        cursada.nota_cursada = 6
        cursada.save()
        for i in range(4):
            InscripcionFinal.objects.create(
                usuario=alumno, llamado=self.mesa(1 + i), aprobada=False, nota=2)
        mesa_nueva = self.mesa(10)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa_nueva]['disponible'])
        self.assertIn('4 oportunidades', items[mesa_nueva]['motivo'])

    def test_recursar_la_cursada_resetea_el_tope(self):
        """4 finales desaprobados, el alumno recursa la cursada: puede volver a rendir."""
        alumno = self.estudiante(66)
        um = usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=2)  # RECURSA
        for _ in range(4):
            # Sin offset: estos llamados quedan fechados ENTRE la creación de
            # `um` y el save() que recursa más abajo, así el reset los deja
            # afuera (ver _detectar_nuevo_ciclo en models.py).
            mesa_vieja = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now())
            InscripcionFinal.objects.create(usuario=alumno, llamado=mesa_vieja, aprobada=False, nota=2)

        puede, _motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertFalse(puede)  # agotado, y además sin cursada aprobada todavía

        um.nota_cursada = 6  # recursó: nueva cursada, ahora aprobada
        um.save()

        puede, motivo = correlativas.puede_rendir(alumno.id, self.materia.id)
        self.assertTrue(puede, motivo)
