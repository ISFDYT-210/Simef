"""
Tests de la baja lógica (#270): dar de baja no borra resultados académicos.

- Las relaciones que llevan a cursadas, notas, inscripciones o actas son
  PROTECT: ni el admin ni la consola pueden borrarlas en cascada.
- "Eliminar" una materia, mesa, inscripción a final o usuario lo da de baja:
  deja de aparecer en los listados y en lo que se ofrece para inscribirse, y
  sus cursadas, notas e inscripciones quedan intactas.
- Una inscripción con resultado y una mesa con resultados no se dan de baja.
- Todo se puede reactivar desde "Dados de baja", y queda en la auditoría.
"""
from datetime import timedelta

from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from inscripcionFinales import correlativas
from inscripcionFinales.forms import InscripcionMateriaForm, MateriaForm, MesaFinalForm
from inscripcionFinales.models import (
    Carrera, EstadoCursada, InscripcionFinal, Materia, MesaFinal, RegistroAuditoria, TribunalMesa,
    Usuario, usuarios_materia,
)
from inscripcionFinales.tests.test_views import crear_usuario
from inscripcionFinales.views import obtener_contexto_reporte


class Escenario(TestCase):
    """Una materia con una cursada aprobada, una mesa pasada con nota y una mesa futura
    con una inscripción todavía sin resultado."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura en Bajas')
        cls.directivo = crear_usuario('dir_baja@test.com', 'Directivo', 'Directora', 40111000)
        cls.preceptor = crear_usuario('prec_bajas@test.com', 'Preceptor', 'Preceptora', 40111001)
        cls.profesor = crear_usuario('prof_bajas@test.com', 'Profesor', 'Profesora', 40111002)
        cls.alumno = crear_usuario('alu_bajas@test.com', 'Estudiante', 'Alumna Uno', 40111003)
        cls.alumno.carrera.add(cls.carrera)

    def setUp(self):
        # anio=2: la inscripción en bloque de primer año no crea cursadas por su cuenta
        self.materia = Materia.objects.create(
            nombre_materia='Química', carrera=self.carrera, anio=2, profesor=self.profesor, inscripcionAbierta=True)
        self.cursada = usuarios_materia.objects.create(usuario=self.alumno, materia=self.materia, nota_cursada=5)
        self.mesa_pasada = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() - timedelta(days=30))
        self.con_nota = InscripcionFinal.objects.create(
            usuario=self.alumno, llamado=self.mesa_pasada, nota=2, aprobada=False)
        # Al minuto justo, para poder escribir el mismo llamado en un formulario
        llamado = (timezone.now() + timedelta(days=20)).replace(second=0, microsecond=0)
        self.mesa_futura = MesaFinal.objects.create(
            materia=self.materia, llamado=llamado, inscripcionAbierta=True, aula='Aula 9')
        self.pendiente = InscripcionFinal.objects.create(usuario=self.alumno, llamado=self.mesa_futura)

    def assertResultadosIntactos(self):
        """Lo que importa de la #270: después de cualquier baja, las notas siguen ahí."""
        self.cursada.refresh_from_db()
        self.con_nota.refresh_from_db()
        self.assertEqual(self.cursada.nota_cursada, 5)
        self.assertEqual(self.con_nota.nota, 2)
        self.assertTrue(self.con_nota.activo)
        self.assertTrue(InscripcionFinal.objects.filter(pk=self.pendiente.pk).exists())
        self.assertTrue(MesaFinal.objects.filter(pk=self.mesa_pasada.pk).exists())

    def ultimo_registro(self):
        return RegistroAuditoria.objects.latest('fecha')

    def puede_entrar(self, usuario):
        """Por la pantalla de login, como cualquier usuario."""
        self.client.logout()
        self.client.post('/accounts/login/', {'username': usuario.dni, 'password': 'secreta'})
        return '_auth_user_id' in self.client.session


class ProtectTest(Escenario):
    """Nada que tenga resultados académicos colgando se puede borrar, ni desde el admin ni desde la consola."""

    def test_no_se_puede_borrar_una_materia_con_cursadas_o_mesas(self):
        with self.assertRaises(ProtectedError):
            self.materia.delete()
        self.assertResultadosIntactos()

    def test_no_se_puede_borrar_una_mesa_con_inscripciones(self):
        with self.assertRaises(ProtectedError):
            self.mesa_pasada.delete()
        self.assertResultadosIntactos()

    def test_no_se_puede_borrar_un_estudiante_con_cursadas_o_finales(self):
        with self.assertRaises(ProtectedError):
            self.alumno.delete()
        self.assertResultadosIntactos()

    def test_no_se_puede_borrar_el_profesor_de_una_materia(self):
        """Antes, borrar al profesor borraba sus materias y todo lo que colgaba de ellas."""
        with self.assertRaises(ProtectedError):
            self.profesor.delete()
        self.assertTrue(Materia.objects.filter(pk=self.materia.pk).exists())

    def test_no_se_puede_borrar_un_docente_que_integro_un_tribunal(self):
        otro = crear_usuario('prof_trib@test.com', 'Profesor', 'Vocal', 40111009)
        TribunalMesa.objects.create(mesa=self.mesa_pasada, docente=otro, rol=TribunalMesa.VOCAL)
        with self.assertRaises(ProtectedError):
            otro.delete()

    def test_no_se_puede_borrar_una_carrera_con_materias(self):
        with self.assertRaises(ProtectedError):
            self.carrera.delete()

    def test_una_materia_sin_nada_asociado_se_puede_borrar(self):
        """PROTECT no frena lo que se cargó por error y no tiene nada colgando."""
        vacia = Materia.objects.create(nombre_materia='Cargada por error', carrera=self.carrera, anio=3)
        vacia.delete()
        self.assertFalse(Materia.objects.filter(pk=vacia.pk).exists())


class BajaMateriaTest(Escenario):

    def test_dar_de_baja_no_borra_nada_y_la_saca_del_listado(self):
        self.client.force_login(self.directivo)
        respuesta = self.client.post(f'/eliminar_materia/{self.materia.pk}/')
        self.assertRedirects(respuesta, '/lista_materias_admin/', fetch_redirect_response=False)
        self.materia.refresh_from_db()
        self.assertFalse(self.materia.activo)
        self.assertFalse(self.materia.inscripcionAbierta)
        self.assertResultadosIntactos()
        self.client.get('/lista_materias_admin/')  # muestra (y consume) el mensaje "Se dio de baja la materia Química…"
        self.assertNotContains(self.client.get('/lista_materias_admin/'), 'Química')

    def test_la_confirmacion_muestra_lo_que_se_conserva(self):
        self.client.force_login(self.directivo)
        respuesta = self.client.get(f'/eliminar_materia/{self.materia.pk}/')
        self.assertContains(respuesta, '1 cursada')
        self.assertContains(respuesta, '2 mesas de final')
        self.assertContains(respuesta, 'Sí, dar de baja')
        self.materia.refresh_from_db()
        self.assertTrue(self.materia.activo)

    def test_dar_de_baja_varias(self):
        otra = Materia.objects.create(nombre_materia='Física', carrera=self.carrera, anio=2)
        self.client.force_login(self.directivo)
        self.client.post('/materias/eliminar_seleccionadas/', {'materia_ids': [self.materia.pk, otra.pk]})
        self.assertEqual(Materia.objects.filter(pk__in=[self.materia.pk, otra.pk], activo=False).count(), 2)
        self.assertResultadosIntactos()

    def test_no_se_ofrece_para_inscribirse_ni_para_crear_mesas(self):
        Materia.objects.filter(pk=self.materia.pk).update(activo=False)
        nuevo = crear_usuario('alu_nuevo@test.com', 'Estudiante', 'Alumno Nuevo', 40111010)
        nuevo.carrera.add(self.carrera)
        ofrecidas = [item['materia'] for item in correlativas.materias_con_requisitos(nuevo)]
        self.assertNotIn(self.materia, ofrecidas)
        self.assertNotIn(self.materia, InscripcionMateriaForm().fields['materia'].queryset)
        self.assertNotIn(self.materia, MesaFinalForm().fields['materia'].queryset)
        # Sus mesas tampoco se le ofrecen al alumno
        mesas = [item['mesa'] for item in correlativas.finales_con_requisitos(self.alumno)]
        self.assertNotIn(self.mesa_futura, mesas)

    def test_editar_una_mesa_de_una_materia_dada_de_baja_sigue_andando(self):
        Materia.objects.filter(pk=self.materia.pk).update(activo=False)
        form = MesaFinalForm(instance=self.mesa_futura)
        self.assertIn(self.materia, form.fields['materia'].queryset)

    def test_no_entra_en_la_inscripcion_en_bloque_de_primer_anio(self):
        de_baja = Materia.objects.create(nombre_materia='Vieja de primero', carrera=self.carrera, anio=1, activo=False)
        de_alta = Materia.objects.create(nombre_materia='Nueva de primero', carrera=self.carrera, anio=1)
        ingresante = crear_usuario('ingresante@test.com', 'Estudiante', 'Ingresante', 40111011)
        ingresante.carrera.add(self.carrera)
        cursadas = set(usuarios_materia.objects.filter(usuario=ingresante).values_list('materia_id', flat=True))
        self.assertIn(de_alta.pk, cursadas)
        self.assertNotIn(de_baja.pk, cursadas)

    def test_la_constancia_la_muestra_solo_a_quien_la_curso(self):
        Materia.objects.filter(pk=self.materia.pk).update(activo=False)
        Materia.objects.create(nombre_materia='Nunca cursada', carrera=self.carrera, anio=2, activo=False)

        def nombres(usuario):
            contexto = obtener_contexto_reporte(usuario)
            return [m['nombre'] for materias in contexto['materias_por_anio'].values() for m in materias]

        self.assertIn('Química', nombres(self.alumno))
        self.assertNotIn('Nunca cursada', nombres(self.alumno))

    def test_reactivarla_la_vuelve_a_mostrar_y_queda_en_la_auditoria(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/eliminar_materia/{self.materia.pk}/')
        respuesta = self.client.post(f'/reactivar/materia/{self.materia.pk}/')
        self.assertRedirects(respuesta, '/dados_de_baja/#materia', fetch_redirect_response=False)
        self.materia.refresh_from_db()
        self.assertTrue(self.materia.activo)
        self.assertEqual(self.ultimo_registro().accion, f'Reactivó la materia Química (id {self.materia.pk})')


class BajaMesaTest(Escenario):

    def test_una_mesa_sin_resultados_se_da_de_baja_sin_tocar_sus_inscripciones(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/delete_mesa/{self.mesa_futura.pk}')
        self.mesa_futura.refresh_from_db()
        self.pendiente.refresh_from_db()
        self.assertFalse(self.mesa_futura.activo)
        self.assertTrue(self.pendiente.activo)  # se esconde con la mesa, no se toca
        self.assertNotIn(self.pendiente, InscripcionFinal.objects.de_alta())
        self.assertResultadosIntactos()
        ids = [fila['id'] for fila in self.client.get('/api/mesas/').json()['results']]
        self.assertNotIn(self.mesa_futura.pk, ids)

    def test_una_mesa_con_resultados_en_el_acta_no_se_da_de_baja(self):
        self.client.force_login(self.preceptor)
        respuesta = self.client.get(f'/delete_mesa/{self.mesa_pasada.pk}')
        self.assertContains(respuesta, 'resultado(s) cargado(s) en el acta')
        self.assertNotContains(respuesta, 'Sí, dar de baja')
        self.client.post(f'/delete_mesa/{self.mesa_pasada.pk}')
        self.mesa_pasada.refresh_from_db()
        self.assertTrue(self.mesa_pasada.activo)
        self.assertResultadosIntactos()

    def test_de_varias_seleccionadas_solo_baja_las_que_no_tienen_resultados(self):
        self.client.force_login(self.preceptor)
        respuesta = self.client.post('/mesas/eliminar_seleccionadas/',
                                     {'mesa_ids': [self.mesa_pasada.pk, self.mesa_futura.pk]}, follow=True)
        self.mesa_pasada.refresh_from_db()
        self.mesa_futura.refresh_from_db()
        self.assertTrue(self.mesa_pasada.activo)
        self.assertFalse(self.mesa_futura.activo)
        self.assertContains(respuesta, 'Se dio de baja 1 mesa.')
        self.assertContains(respuesta, 'No se dio de baja la mesa de Química')

    def test_el_alumno_puede_anotarse_en_otra_mesa_de_la_materia(self):
        MesaFinal.objects.filter(pk=self.mesa_futura.pk).update(activo=False)
        pendientes = InscripcionFinal.objects.de_alta().sin_resultado().filter(usuario=self.alumno)
        self.assertFalse(pendientes.exists())

    def test_una_mesa_anulada_no_ocupa_el_aula_ni_el_horario(self):
        MesaFinal.objects.filter(pk=self.mesa_futura.pk).update(activo=False)
        form = MesaFinalForm(data={
            'materia': self.materia.pk,
            'llamado': timezone.localtime(self.mesa_futura.llamado).strftime('%Y-%m-%dT%H:%M'),
            'aula': 'Aula 9', 'sede': '',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_al_reactivarla_vuelven_sus_inscripciones(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/delete_mesa/{self.mesa_futura.pk}')
        self.client.post(f'/reactivar/mesa/{self.mesa_futura.pk}/')
        self.assertIn(self.pendiente, InscripcionFinal.objects.de_alta())

    def test_no_se_reactiva_si_ya_hay_otra_mesa_en_ese_horario(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/delete_mesa/{self.mesa_futura.pk}')
        MesaFinal.objects.create(materia=self.materia, llamado=self.mesa_futura.llamado)
        respuesta = self.client.post(f'/reactivar/mesa/{self.mesa_futura.pk}/', follow=True)
        self.assertContains(respuesta, 'Ya hay otra mesa de Química en ese mismo día y horario')
        self.mesa_futura.refresh_from_db()
        self.assertFalse(self.mesa_futura.activo)


class BajaInscripcionFinalTest(Escenario):

    def test_con_resultado_no_se_da_de_baja(self):
        self.client.force_login(self.preceptor)
        for url in (f'/eliminar_inscripcion_final/{self.con_nota.pk}/', f'/delete_inscripcion/{self.con_nota.pk}'):
            respuesta = self.client.post(url, follow=True)
            self.assertContains(respuesta, 'es parte del acta')
        self.assertResultadosIntactos()

    def test_sin_resultado_se_da_de_baja_y_el_alumno_puede_volver_a_anotarse(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/eliminar_inscripcion_final/{self.pendiente.pk}/')
        self.pendiente.refresh_from_db()
        self.assertFalse(self.pendiente.activo)
        ids = [fila['id'] for fila in self.client.get('/api/inscripciones/').json()['results']]
        self.assertNotIn(self.pendiente.pk, ids)
        self.assertNotContains(self.client.get(f'/acta_volante/{self.mesa_futura.pk}'), 'Alumna Uno')

        self.client.force_login(self.alumno)
        self.client.post(f'/inscribirse_final/{self.mesa_futura.pk}')
        nuevas = InscripcionFinal.objects.de_alta().filter(usuario=self.alumno, llamado=self.mesa_futura)
        self.assertEqual(nuevas.count(), 1)
        self.assertResultadosIntactos()

    def test_no_se_carga_nota_en_una_inscripcion_dada_de_baja(self):
        InscripcionFinal.objects.filter(pk=self.pendiente.pk).update(activo=False)
        self.client.force_login(self.preceptor)
        self.assertEqual(self.client.get(f'/cargar_nota_final/{self.pendiente.pk}/').status_code, 404)

    def test_no_se_reactiva_si_el_alumno_ya_se_anoto_en_otra_mesa(self):
        InscripcionFinal.objects.filter(pk=self.pendiente.pk).update(activo=False)
        otra_mesa = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() + timedelta(days=40))
        InscripcionFinal.objects.create(usuario=self.alumno, llamado=otra_mesa)
        self.client.force_login(self.preceptor)
        respuesta = self.client.post(f'/reactivar/inscripcion/{self.pendiente.pk}/', follow=True)
        self.assertContains(respuesta, 'ya está inscripto en otra mesa de Química')
        self.pendiente.refresh_from_db()
        self.assertFalse(self.pendiente.activo)


class BajaUsuarioTest(Escenario):

    def test_dar_de_baja_no_borra_su_historial_y_no_puede_entrar(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/delete_user/{self.alumno.pk}')
        self.alumno.refresh_from_db()
        self.assertFalse(self.alumno.is_active)
        self.assertResultadosIntactos()
        ids = [fila['id'] for fila in self.client.get('/api/usuarios/').json()['results']]
        self.assertNotIn(self.alumno.pk, ids)
        self.assertFalse(self.puede_entrar(self.alumno))

    def test_abrir_la_pantalla_no_da_de_baja(self):
        """Antes la pantalla se confirmaba sola con JavaScript."""
        self.client.force_login(self.directivo)
        respuesta = self.client.get(f'/delete_user/{self.alumno.pk}')
        self.assertContains(respuesta, 'Sí, dar de baja')
        self.assertNotContains(respuesta, '.click()')
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.is_active)

    def test_no_se_puede_dar_de_baja_a_si_mismo(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/delete_user/{self.directivo.pk}')
        self.directivo.refresh_from_db()
        self.assertTrue(self.directivo.is_active)

    def test_dar_de_baja_varios(self):
        otro = crear_usuario('alu_otro@test.com', 'Estudiante', 'Alumno Dos', 40111012)
        self.client.force_login(self.directivo)
        self.client.post('/eliminar_usuarios_seleccionados/', {'usuarios_ids': [self.alumno.pk, otro.pk]})
        self.assertEqual(Usuario.objects.filter(pk__in=[self.alumno.pk, otro.pk], is_active=False).count(), 2)
        self.assertResultadosIntactos()

    def test_no_se_ofrece_para_asignarle_cosas(self):
        Usuario.objects.filter(pk=self.profesor.pk).update(is_active=False)
        Usuario.objects.filter(pk=self.alumno.pk).update(is_active=False)
        self.assertNotIn(self.profesor, Usuario.obtener_profesores())
        self.assertNotIn(self.alumno, InscripcionMateriaForm().fields['usuario'].queryset)
        self.assertNotIn(self.profesor, MateriaForm().fields['profesor'].queryset)
        # Pero editar una materia suya no obliga a cambiarle el profesor
        self.assertIn(self.profesor, MateriaForm(instance=self.materia).fields['profesor'].queryset)

    def test_reactivado_vuelve_a_entrar(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/delete_user/{self.alumno.pk}')
        self.client.post(f'/reactivar/usuario/{self.alumno.pk}/')
        self.assertTrue(self.puede_entrar(self.alumno))


class AbandonoNoBorraFinalesTest(Escenario):
    """Antes, dar de baja una cursada (abandono) borraba TODAS las inscripciones a final de esa materia."""

    def test_conserva_los_finales_con_nota_y_da_de_baja_solo_los_pendientes(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/eliminar_inscripcion_materia/{self.cursada.pk}/')
        self.cursada.refresh_from_db()
        self.pendiente.refresh_from_db()
        self.assertEqual(self.cursada.estado, EstadoCursada.ABANDONO)
        self.assertFalse(self.pendiente.activo)
        self.assertResultadosIntactos()
        self.assertIn('Inscripciones a final sin resultado dadas de baja: 1', self.ultimo_registro().valor_nuevo)


class PantallaDadosDeBajaTest(Escenario):

    def setUp(self):
        super().setUp()
        Materia.objects.filter(pk=self.materia.pk).update(activo=False)
        Usuario.objects.filter(pk=self.profesor.pk).update(is_active=False)

    def test_cada_uno_ve_lo_que_puede_gestionar(self):
        self.client.force_login(self.directivo)
        respuesta = self.client.get('/dados_de_baja/')
        self.assertContains(respuesta, 'Química')
        self.assertContains(respuesta, 'Profesora')

        self.client.force_login(self.preceptor)
        respuesta = self.client.get('/dados_de_baja/')
        self.assertContains(respuesta, 'Mesas de final')
        self.assertNotContains(respuesta, 'id="usuario"')
        self.assertNotContains(respuesta, 'id="materia"')
        self.assertEqual(self.client.post(f'/reactivar/usuario/{self.profesor.pk}/').status_code, 403)

    def test_estudiantes_y_profesores_no_entran(self):
        for usuario in (self.alumno, crear_usuario('prof_x@test.com', 'Profesor', 'Otro', 40111013)):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get('/dados_de_baja/').status_code, 403)

    def test_reactivar_solo_por_post_y_con_un_tipo_conocido(self):
        self.client.force_login(self.directivo)
        self.assertEqual(self.client.get(f'/reactivar/materia/{self.materia.pk}/').status_code, 405)
        self.assertEqual(self.client.post(f'/reactivar/carrera/{self.carrera.pk}/').status_code, 404)
        # Lo que está de alta no se "reactiva"
        self.assertEqual(self.client.post(f'/reactivar/mesa/{self.mesa_futura.pk}/').status_code, 404)


class VersionAnteriorPuedeSeguirInsertandoTest(TestCase):
    """Las migraciones corren antes que el código nuevo: mientras se publica, la versión
    anterior (que no conoce las columnas nuevas) tiene que poder seguir insertando."""

    def insertar(self, tabla, columnas, valores):
        from django.db import connection
        nombres = ', '.join(connection.ops.quote_name(c) for c in columnas)
        marcas = ', '.join(['%s'] * len(valores))
        with connection.cursor() as cursor:
            cursor.execute(f'INSERT INTO {connection.ops.quote_name(tabla)} ({nombres}) VALUES ({marcas})', valores)

    def test_materias_mesas_e_inscripciones_quedan_de_alta(self):
        self.insertar(Materia._meta.db_table, ['nombre_materia', 'inscripcionAbierta', 'Horario', 'anio', 'dia'],
                      ['Insertada por la versión anterior', False, '12:00', 1, 'Lunes'])
        self.assertTrue(Materia.objects.get(nombre_materia='Insertada por la versión anterior').activo)

