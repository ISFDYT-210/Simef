"""
Tests de la pantalla para editar una inscripción a final (#278).

Sigue las mismas reglas que el resto de la gestión de mesas: la usa quien
gestiona mesas (Directivo, Secretario, Preceptor), no cualquier cuenta. Sirve
para pasar la inscripción a otra mesa de la misma materia: no cambia el
estudiante, no toca inscripciones con resultado ni dadas de baja, y el cambio
queda en la auditoría.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from inscripcionFinales.forms import InscripcionFinalForm
from inscripcionFinales.models import (
    Carrera, InscripcionFinal, Materia, MesaFinal, RegistroAuditoria, usuarios_materia,
)
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

    def test_pasa_a_otra_mesa_de_la_misma_materia_y_queda_en_la_auditoria(self):
        self.client.force_login(self.preceptor)
        respuesta = self.client.post(self.url, {'llamado': self.otra_mesa.pk})
        self.assertRedirects(respuesta, '/inscripcion_finales_lista/', fetch_redirect_response=False)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.llamado, self.otra_mesa)
        registro = RegistroAuditoria.objects.latest('fecha')
        self.assertEqual(registro.accion, 'Pasó a Alumna Inscripta a otra mesa de Biología')
        self.assertEqual(registro.objeto_id, str(self.inscripcion.pk))
        self.assertIn(f'(id {self.mesa.pk})', registro.valor_anterior)
        self.assertIn(f'(id {self.otra_mesa.pk})', registro.valor_nuevo)

    def test_no_cambia_el_estudiante(self):
        self.client.force_login(self.preceptor)
        self.client.post(self.url, {'usuario': self.otro.pk, 'llamado': self.otra_mesa.pk})
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.usuario, self.alumna)

    def test_solo_ofrece_mesas_de_la_misma_materia(self):
        otra_materia = Materia.objects.create(nombre_materia='Física', carrera=self.carrera, anio=2)
        mesa_ajena = MesaFinal.objects.create(
            materia=otra_materia, llamado=timezone.now() + timedelta(days=12), inscripcionAbierta=True)
        ofrecidas = set(InscripcionFinalForm(instance=self.inscripcion).fields['llamado'].queryset)
        self.assertEqual(ofrecidas, {self.mesa, self.otra_mesa})
        self.client.force_login(self.preceptor)
        self.client.post(self.url, {'llamado': mesa_ajena.pk})
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.llamado, self.mesa)

    def test_con_resultado_no_se_cambia_de_mesa(self):
        InscripcionFinal.objects.filter(pk=self.inscripcion.pk).update(nota=8, aprobada=True)
        self.client.force_login(self.preceptor)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'es parte del acta')
        self.assertNotContains(respuesta, 'Guardar')
        self.client.post(self.url, {'llamado': self.otra_mesa.pk})
        self.inscripcion.refresh_from_db()
        self.assertEqual((self.inscripcion.llamado, self.inscripcion.nota), (self.mesa, 8))

    def test_dada_de_baja_no_se_edita(self):
        InscripcionFinal.objects.filter(pk=self.inscripcion.pk).update(activo=False)
        self.client.force_login(self.preceptor)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'llamado': self.otra_mesa.pk}).status_code, 404)

    def test_guardar_sin_cambiar_de_mesa_no_deja_registro(self):
        antes = RegistroAuditoria.objects.count()
        self.client.force_login(self.preceptor)
        self.client.post(self.url, {'llamado': self.mesa.pk})
        self.assertEqual(RegistroAuditoria.objects.count(), antes)
