"""
Tests de validar_inscripcion_final y del widget de materias del alta de mesa.

validar_inscripcion_final estaba definida dos veces en views.py: Python se
quedaba con la última y la otra quedaba muerta, pese a comportarse distinto
(ignoraba la modalidad Libre y bloqueaba a quien tuviera cualquier nota de
final, incluso desaprobada). Se eliminó la muerta; estos tests fijan el
comportamiento de la que quedó, para que no se reintroduzca la confusión.

Correr con:
    python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
"""
from django.test import TestCase

from inscripcionFinales.forms import MesaFinalForm
from inscripcionFinales.models import (
    Carrera, Materia, MateriaCorrelativa, Usuario, usuarios_materia,
)
from inscripcionFinales.views import validar_inscripcion_final


class ValidarInscripcionFinalTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)
        cls.correlativa = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)

    def estudiante(self, dni):
        return Usuario.objects.create(
            email=f'e{dni}@test.com', username=f'e{dni}',
            nombre_completo=f'Estudiante {dni}', rol='Estudiante', dni=dni,
        )

    def test_no_inscripto_a_la_materia_no_puede(self):
        alumno = self.estudiante(200)
        self.assertFalse(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_sin_nota_de_cursada_no_puede(self):
        alumno = self.estudiante(201)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia)
        self.assertFalse(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_con_cursada_suficiente_puede(self):
        alumno = self.estudiante(202)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=7)
        self.assertTrue(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_modalidad_libre_no_necesita_nota_de_cursada(self):
        """La versión que quedó respeta 'Libre'; la que se borró lo ignoraba."""
        alumno = self.estudiante(203)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, modalidad='Libre')
        self.assertTrue(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_si_ya_aprobo_el_final_no_se_reinscribe(self):
        alumno = self.estudiante(204)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=8, nota_final=7)
        self.assertFalse(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_si_desaprobo_el_final_puede_volver_a_rendir(self):
        """La versión borrada bloqueaba con cualquier nota, incluso un 2."""
        alumno = self.estudiante(205)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=8, nota_final=2)
        self.assertTrue(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_correlativa_sin_aprobar_bloquea(self):
        alumno = self.estudiante(206)
        MateriaCorrelativa.objects.create(
            materia=self.materia, materia_correlativa=self.correlativa)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=8)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.correlativa, nota_cursada=8, nota_final=2)

        self.assertFalse(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_correlativa_aprobada_habilita(self):
        alumno = self.estudiante(207)
        MateriaCorrelativa.objects.create(
            materia=self.materia, materia_correlativa=self.correlativa)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=8)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.correlativa, nota_cursada=8, nota_final=6)

        self.assertTrue(validar_inscripcion_final(alumno.id, self.materia.id))

    def test_correlativa_que_ni_curso_bloquea(self):
        alumno = self.estudiante(208)
        MateriaCorrelativa.objects.create(
            materia=self.materia, materia_correlativa=self.correlativa)
        usuarios_materia.objects.create(
            usuario=alumno, materia=self.materia, nota_cursada=8)

        self.assertFalse(validar_inscripcion_final(alumno.id, self.materia.id))


class MesaFinalFormTest(TestCase):
    """El select de materias expone carrera y año para el filtro visual del alta."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.sin_carrera = Materia.objects.create(
            nombre_materia='Suelta', carrera=None, anio=3)

    def test_cada_opcion_trae_su_carrera_y_su_anio(self):
        html = str(MesaFinalForm()['materia'])

        self.assertIn(f'value="{self.materia.id}"', html)
        self.assertIn(f'data-carrera="{self.carrera.id}"', html)
        self.assertIn('data-anio="1"', html)

    def test_materia_sin_carrera_no_rompe(self):
        html = str(MesaFinalForm()['materia'])
        self.assertIn(f'value="{self.sin_carrera.id}"', html)
        self.assertIn('data-anio="3"', html)
