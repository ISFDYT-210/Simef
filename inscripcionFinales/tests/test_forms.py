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
from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from inscripcionFinales.forms import MesaFinalForm, profile_students_form, registri_user_form
from inscripcionFinales.models import (
    Carrera, Materia, MateriaCorrelativa, MesaFinal, Usuario, usuarios_materia,
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


class MesaFinalFormSinDuplicadosTest(TestCase):
    """No puede haber dos mesas de la MISMA materia en el MISMO día y horario."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.otra_materia = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)

    def aware(self, *args):
        return timezone.make_aware(datetime(*args))

    def datos(self, materia, llamado, **overrides):
        datos = {
            'materia': materia.id, 'llamado': llamado, 'aula': '', 'sede': '',
            'inscripcionAbierta': False,
        }
        datos.update(overrides)
        return datos

    def test_misma_materia_mismo_dia_y_horario_se_rechaza(self):
        MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))

        form = MesaFinalForm(self.datos(self.materia, '2030-11-10T09:00'))

        self.assertFalse(form.is_valid())
        self.assertIn('mismo día y horario', form.errors['llamado'][0])

    def test_misma_materia_distinto_horario_se_permite(self):
        MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))

        form = MesaFinalForm(self.datos(self.materia, '2030-11-10T15:00'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_misma_materia_distinto_dia_se_permite(self):
        MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))

        form = MesaFinalForm(self.datos(self.materia, '2030-11-11T09:00'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_distinta_materia_mismo_dia_y_horario_se_permite(self):
        MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T09:00'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_editar_una_mesa_sin_cambiar_el_llamado_no_choca_consigo_misma(self):
        mesa = MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))

        form = MesaFinalForm(self.datos(self.materia, '2030-11-10T09:00'), instance=mesa)

        self.assertTrue(form.is_valid(), form.errors)

    def test_editar_una_mesa_para_chocar_con_otra_existente_se_rechaza(self):
        mesa = MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0))
        MesaFinal.objects.create(materia=self.materia, llamado=self.aware(2030, 11, 11, 9, 0))

        form = MesaFinalForm(self.datos(self.materia, '2030-11-11T09:00'), instance=mesa)

        self.assertFalse(form.is_valid())
        self.assertIn('mismo día y horario', form.errors['llamado'][0])


class MesaFinalFormAulaSinSuperposicionTest(TestCase):
    """
    Dos mesas (de cualquier materia) no pueden compartir aula si sus horarios
    se superponen. Toda mesa dura MesaFinal.DURACION (2hs, fija para todas:
    no hay hora de fin en la base).
    """

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura')
        cls.materia = Materia.objects.create(
            nombre_materia='Programación I', carrera=cls.carrera, anio=1)
        cls.otra_materia = Materia.objects.create(
            nombre_materia='Programación II', carrera=cls.carrera, anio=2)

    def aware(self, *args):
        return timezone.make_aware(datetime(*args))

    def datos(self, materia, llamado, aula, **overrides):
        datos = {
            'materia': materia.id, 'llamado': llamado, 'aula': aula, 'sede': '',
            'inscripcionAbierta': False,
        }
        datos.update(overrides)
        return datos

    def test_misma_aula_mismo_horario_distinta_materia_se_rechaza(self):
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T09:00', 'Aula 3'))

        self.assertFalse(form.is_valid())
        self.assertIn('ocupada', form.errors['aula'][0])

    def test_misma_aula_horario_superpuesto_parcialmente_se_rechaza(self):
        """Mesa existente 09:00-11:00; una nueva a las 10:00 (10:00-12:00) se superpone."""
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T10:00', 'Aula 3'))

        self.assertFalse(form.is_valid())
        self.assertIn('ocupada', form.errors['aula'][0])

    def test_misma_aula_justo_despues_de_que_termine_la_anterior_se_permite(self):
        """Mesa existente 09:00-11:00; una nueva arranca exactamente a las 11:00: no se superponen."""
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T11:00', 'Aula 3'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_misma_aula_otro_dia_se_permite(self):
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-11T09:00', 'Aula 3'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_distinta_aula_mismo_horario_se_permite(self):
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T09:00', 'Aula 4'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_aula_no_valida_superposicion(self):
        MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='')

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T09:00', ''))

        self.assertTrue(form.is_valid(), form.errors)

    def test_mesa_no_vigente_no_ocupa_el_aula(self):
        mesa = MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')
        mesa.vigente = False
        mesa.save()

        form = MesaFinalForm(self.datos(self.otra_materia, '2030-11-10T09:00', 'Aula 3'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_editar_una_mesa_sin_cambiar_nada_no_choca_consigo_misma(self):
        mesa = MesaFinal.objects.create(
            materia=self.materia, llamado=self.aware(2030, 11, 10, 9, 0), aula='Aula 3')

        form = MesaFinalForm(self.datos(self.materia, '2030-11-10T09:00', 'Aula 3'), instance=mesa)

        self.assertTrue(form.is_valid(), form.errors)


class ProfileStudentsFormTest(TestCase):
    """
    telefono_1/telefono_2 son opcionales en el modelo (blank=True, null=True)
    y el propio template dice "los campos vacíos se pueden completar más
    tarde" — pero el form los pedía como obligatorios, así que cualquier
    edición (incluido un simple cambio de rol) quedaba bloqueada si a
    alguien le faltaba uno de esos dos datos. El DNI, en cambio, es el
    identificador de login: este form lo deja fijo (disabled) aunque llegue
    otro valor en el POST.
    """

    def datos_base(self, usuario, **overrides):
        datos = {
            'username': usuario.username, 'nombre_completo': usuario.nombre_completo,
            'fecha_nac': '', 'dni': usuario.dni, 'direccion': '', 'localidad': '', 'ciudad': '',
            'nacionalidad': '', 'telefono_1': '', 'telefono_2': '', 'estado_civil': '', 'sexo': '',
        }
        datos.update(overrides)
        return datos

    def test_valido_con_telefonos_en_blanco(self):
        usuario = Usuario.objects.create(
            email='sintelefono@test.com', username='sintelefono',
            nombre_completo='Sin Telefono', rol='Profesor', dni='50505050',
        )
        form = profile_students_form(self.datos_base(usuario), instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)

    def test_el_dni_no_se_puede_modificar_desde_el_form(self):
        usuario = Usuario.objects.create(
            email='condni@test.com', username='condni', nombre_completo='Con Dni',
            rol='Profesor', dni='12345678',
        )
        form = profile_students_form(self.datos_base(usuario, dni='99999999'), instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        guardado = form.save()
        self.assertEqual(guardado.dni, '12345678')

    def test_email_en_blanco_se_guarda_como_none_no_como_string_vacio(self):
        """email es nullable+unique: guardar '' directo chocaría entre dos cuentas sin email."""
        usuario = Usuario.objects.create(
            username='sinmail', nombre_completo='Sin Mail', rol='Profesor', dni='60606060',
        )
        form = profile_students_form(self.datos_base(usuario, email=''), instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        guardado = form.save()
        self.assertIsNone(guardado.email)


class CredencialesFueraDeLosLogsTest(TestCase):
    """
    El alta de un usuario escribía su email y su contraseña en los logs del
    servidor, que en Vercel ve cualquiera con acceso al panel (#183).
    """

    PASSWORD = 'Clave-De-Prueba-123'

    def setUp(self):
        self.usuario = Usuario.objects.create(dni='4500', email='alta@test.com', nombre_completo='Alta Nueva')
        self.form = registri_user_form()

    def enviar_y_capturar(self):
        import contextlib
        import io
        salida = io.StringIO()
        with self.assertLogs('inscripcionFinales.forms', level='DEBUG') as logs, contextlib.redirect_stdout(salida):
            enviado = self.form.enviar_credenciales_email(self.usuario, self.PASSWORD)
        return enviado, salida.getvalue() + '\n'.join(logs.output)

    def test_envio_correcto_no_deja_la_contrasena_ni_el_email(self):
        enviado, registrado = self.enviar_y_capturar()
        self.assertTrue(enviado)
        self.assertNotIn(self.PASSWORD, registrado)
        self.assertNotIn(self.usuario.email, registrado)

    def test_envio_fallido_no_deja_la_contrasena_ni_el_email(self):
        from unittest import mock
        with mock.patch('inscripcionFinales.forms.send_mail', side_effect=OSError('sin SMTP')):
            enviado, registrado = self.enviar_y_capturar()
        self.assertFalse(enviado)
        self.assertNotIn(self.PASSWORD, registrado)
        self.assertNotIn(self.usuario.email, registrado)
