"""
Tests de la pantalla para editar una inscripción a final (#278).

Sigue las mismas reglas que el resto de la gestión de mesas: la usa quien
gestiona mesas (Directivo, Secretario, Preceptor), no cualquier cuenta.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from inscripcionFinales.models import Carrera, InscripcionFinal, Materia, MesaFinal, usuarios_materia
from inscripcionFinales.tests.test_views import crear_usuario


class EditarInscripcionFinalTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura en Mesas')
        cls.materia = Materia.objects.create(nombre_materia='Biología', carrera=cls.carrera, anio=2)
        cls.preceptor = crear_usuario('prec_edit@test.com', 'Preceptor', 'Preceptora', 41000001)
        cls.profesor = crear_usuario('prof_edit@test.com', 'Profesor', 'Profesora', 41000002)
        cls.alumna = crear_usuario('alu_edit@test.com', 'Estudiante', 'Alumna Inscripta', 41000003)
        cls.otro = crear_usuario('otro_edit@test.com', 'Estudiante', 'Otro Alumno', 41000004)
        for alumno in (cls.alumna, cls.otro):
            alumno.carrera.add(cls.carrera)
            usuarios_materia.objects.create(usuario=alumno, materia=cls.materia, nota_cursada=5)

    def setUp(self):
        self.mesa = MesaFinal.objects.create(
            materia=self.materia, llamado=timezone.now() + timedelta(days=10), inscripcionAbierta=True)
        self.otra_mesa = MesaFinal.objects.create(
            materia=self.materia, llamado=timezone.now() + timedelta(days=17), inscripcionAbierta=True)
        self.inscripcion = InscripcionFinal.objects.create(usuario=self.alumna, llamado=self.mesa)
        self.url = f'/edit_inscr/{self.inscripcion.pk}'

    def test_un_estudiante_no_puede_usarla(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        respuesta = self.client.post(self.url, {'usuario': self.otro.pk, 'llamado': self.otra_mesa.pk})
        self.assertEqual(respuesta.status_code, 403)
        self.inscripcion.refresh_from_db()
        self.assertEqual((self.inscripcion.usuario, self.inscripcion.llamado), (self.alumna, self.mesa))

    def test_un_profesor_no_puede_usarla(self):
        self.client.force_login(self.profesor)
        respuesta = self.client.post(self.url, {'usuario': self.alumna.pk, 'llamado': self.otra_mesa.pk})
        self.assertEqual(respuesta.status_code, 403)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.llamado, self.mesa)

    def test_el_preceptor_la_ve(self):
        """Antes la pantalla se mostraba solo a cuentas de administración del sistema (is_staff)."""
        self.client.force_login(self.preceptor)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Guardar')
