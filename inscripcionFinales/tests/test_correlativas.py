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

    def test_materia_con_cursada_activa_no_aparece_en_el_desglose(self):
        """Ya la está cursando: no es candidata a "inscribirse", no tiene sentido listarla acá."""
        alumno = self.estudiante(42)
        alumno.carrera.add(self.carrera)  # la señal la inscribe en bloque (EN_CURSO)
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

    def test_sin_nota_de_cursada_suficiente(self):
        alumno = self.estudiante(51)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(nota_cursada=5)
        mesa = self.mesa(self.primero)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('≥ 7', items[mesa]['motivo'])

    def test_correlativa_sin_final_aprobado(self):
        alumno = self.estudiante(52)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(nota_cursada=8)
        usuarios_materia.objects.create(usuario=alumno, materia=self.segundo, nota_cursada=8)
        mesa = self.mesa(self.segundo)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('Programación I', items[mesa]['motivo'])

    def test_cumple_todo_queda_disponible(self):
        alumno = self.estudiante(53)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(nota_cursada=8)
        mesa = self.mesa(self.primero)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertTrue(items[mesa]['disponible'])
        self.assertIsNone(items[mesa]['motivo'])

    def test_mesa_sin_inscripcion_abierta(self):
        alumno = self.estudiante(54)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(nota_cursada=8)
        mesa = self.mesa(self.primero, inscripcion_abierta=False)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa]['disponible'])
        self.assertIn('no está abierta', items[mesa]['motivo'])

    def test_ya_inscripto_en_una_mesa_de_la_materia(self):
        alumno = self.estudiante(55)
        alumno.carrera.add(self.carrera)
        usuarios_materia.objects.filter(usuario=alumno, materia=self.primero).update(nota_cursada=8)
        mesa_vieja = self.mesa(self.primero, dias=2)
        InscripcionFinal.objects.create(usuario=alumno, llamado=mesa_vieja)
        mesa_nueva = self.mesa(self.primero, dias=10)
        items = {i['mesa']: i for i in correlativas.finales_con_requisitos(alumno)}
        self.assertFalse(items[mesa_nueva]['disponible'])
        self.assertIn('Ya estás inscripto', items[mesa_nueva]['motivo'])
