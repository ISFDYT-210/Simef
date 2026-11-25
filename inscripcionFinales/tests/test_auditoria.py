"""
Tests del registro de auditoría (#271).

- Guarda el autor (DNI, nombre y rol) en el registro: no se pierde si se borra la cuenta.
- Guarda valor anterior, valor nuevo y motivo, además del texto de la acción.
- No se modifica ni se borra: lo impide el modelo y, en PostgreSQL, un trigger.
- Ya no borra sola los registros de más de un año.
- Las eliminaciones y las ediciones de notas dejan registro, con lo que arrastró
  el borrado en cascada.
"""
from datetime import timedelta

from django.db import IntegrityError, InternalError, connection, transaction
from django.db.utils import DatabaseError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from inscripcionFinales.audit import registrar_auditoria
from inscripcionFinales.models import (
    Carrera, InscripcionFinal, Materia, MesaFinal, RegistroAuditoria,
    RegistroAuditoriaInmodificable, Usuario, usuarios_materia,
)
from inscripcionFinales.tests.test_views import crear_usuario

TABLA = RegistroAuditoria._meta.db_table


def request_de(usuario):
    request = RequestFactory().get('/')
    request.user = usuario
    return request


class RegistrarAuditoriaTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.preceptor = crear_usuario('prec_audit@test.com', 'Preceptor', 'Preceptora Auditada', 30111222)

    def test_guarda_el_autor_y_los_valores(self):
        registro = registrar_auditoria(
            request_de(self.preceptor), 'Corrigió una nota', 'InscripcionFinal', 7,
            valor_anterior='nota 3', valor_nuevo='nota 6', motivo='Error de tipeo',
        )
        registro.refresh_from_db()
        self.assertEqual(registro.autor_dni, '30111222')
        self.assertEqual(registro.autor_nombre, 'Preceptora Auditada')
        self.assertEqual(registro.autor_rol, 'Preceptor')
        self.assertEqual((registro.valor_anterior, registro.valor_nuevo, registro.motivo),
                         ('nota 3', 'nota 6', 'Error de tipeo'))

    def test_ya_no_borra_los_registros_de_mas_de_un_anio(self):
        """Antes cada registro nuevo borraba los de más de 365 días. La retención la define la institución."""
        hace_dos_anios = timezone.now() - timedelta(days=730)
        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO "{TABLA}" (accion, modelo_afectado, objeto_id, autor_dni, autor_nombre, autor_rol, '
                'valor_anterior, valor_nuevo, motivo, fecha) '
                "VALUES ('Acción vieja', '', '', '', '', '', '', '', '', %s)", [hace_dos_anios])
        registrar_auditoria(request_de(self.preceptor), 'Acción nueva')
        self.assertTrue(RegistroAuditoria.objects.filter(accion='Acción vieja').exists())


class RegistroInmodificableTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.preceptor = crear_usuario('prec_inmod@test.com', 'Preceptor', 'Preceptor Inmod', 30222333)

    def setUp(self):
        self.registro = registrar_auditoria(request_de(self.preceptor), 'Acción original')

    def test_no_se_puede_modificar_desde_el_modelo(self):
        self.registro.accion = 'Acción cambiada'
        with self.assertRaises(RegistroAuditoriaInmodificable):
            self.registro.save()
        with self.assertRaises(RegistroAuditoriaInmodificable):
            RegistroAuditoria.objects.filter(pk=self.registro.pk).update(accion='Otra')

    def test_no_se_puede_borrar_desde_el_modelo(self):
        with self.assertRaises(RegistroAuditoriaInmodificable):
            self.registro.delete()
        with self.assertRaises(RegistroAuditoriaInmodificable):
            RegistroAuditoria.objects.filter(pk=self.registro.pk).delete()
        self.assertTrue(RegistroAuditoria.objects.filter(pk=self.registro.pk).exists())

    def test_en_postgresql_la_base_tambien_lo_impide(self):
        """El trigger de la migración 0024 frena a quien escriba SQL directo contra la tabla."""
        if connection.vendor != 'postgresql':
            self.skipTest('El trigger existe solo en PostgreSQL (producción y CI).')
        for sql in (f'UPDATE "{TABLA}" SET accion = %s WHERE id = %s', f'DELETE FROM "{TABLA}" WHERE id = %s'):
            params = ['Cambiada', self.registro.pk] if sql.startswith('UPDATE') else [self.registro.pk]
            with self.subTest(sql=sql.split()[0]):
                with self.assertRaises((InternalError, IntegrityError, DatabaseError)):
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute(sql, params)
        self.registro.refresh_from_db()
        self.assertEqual(self.registro.accion, 'Acción original')


class AutorConservadoTest(TestCase):
    """Si se borra la cuenta, el registro sigue diciendo quién fue y sigue en el listado."""

    @classmethod
    def setUpTestData(cls):
        cls.directivo = crear_usuario('dir_autor@test.com', 'Directivo', 'Directora Lista', 30333444)

    def test_el_autor_queda_y_el_registro_sigue_en_el_listado(self):
        preceptor = crear_usuario('prec_baja@test.com', 'Preceptor', 'Preceptor Dado de Baja', 30444555)
        registro = registrar_auditoria(request_de(preceptor), 'Acción antes de la baja')
        preceptor.delete()  # on_delete=SET_NULL: en PostgreSQL, el trigger tiene que dejarlo pasar

        registro.refresh_from_db()
        self.assertIsNone(registro.usuario)
        self.assertEqual((registro.autor_dni, registro.autor_nombre, registro.autor_rol),
                         ('30444555', 'Preceptor Dado de Baja', 'Preceptor'))

        self.client.force_login(self.directivo)
        respuesta = self.client.get('/auditoria/')
        self.assertContains(respuesta, 'Acción antes de la baja')
        self.assertContains(respuesta, 'Preceptor Dado de Baja')
        self.assertContains(respuesta, 'cuenta dada de baja')

    def test_se_puede_buscar_por_dni_del_autor(self):
        preceptor = crear_usuario('prec_busca@test.com', 'Preceptor', 'Preceptor Buscado', 30555666)
        registrar_auditoria(request_de(preceptor), 'Acción a buscar')
        self.client.force_login(self.directivo)
        self.assertContains(self.client.get('/auditoria/', {'search': '30555666'}), 'Acción a buscar')


class AccionesCriticasDejanRegistroTest(TestCase):
    """Las eliminaciones y las ediciones de notas quedan en la auditoría, con qué arrastró el borrado."""

    @classmethod
    def setUpTestData(cls):
        cls.carrera = Carrera.objects.create(nombre_carrera='Tecnicatura Auditoría')
        cls.directivo = crear_usuario('dir_crit@test.com', 'Directivo', 'Directivo Crit', 30666777)
        cls.preceptor = crear_usuario('prec_crit@test.com', 'Preceptor', 'Preceptor Crit', 30777888)
        cls.estudiante = crear_usuario('est_crit@test.com', 'Estudiante', 'Estudiante Crit', 30888999)

    def setUp(self):
        self.materia = Materia.objects.create(nombre_materia='Base de Datos', carrera=self.carrera, anio=2)
        self.mesa = MesaFinal.objects.create(materia=self.materia, llamado=timezone.now() - timedelta(days=3))
        self.cursada = usuarios_materia.objects.create(usuario=self.estudiante, materia=self.materia, nota_cursada=7)
        self.inscripcion = InscripcionFinal.objects.create(
            usuario=self.estudiante, llamado=self.mesa, nota=8, aprobada=True)

    def ultimo(self):
        return RegistroAuditoria.objects.latest('fecha')

    def test_eliminar_una_materia_registra_lo_que_arrastro(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/eliminar_materia/{self.materia.pk}/')
        registro = self.ultimo()
        self.assertIn('Eliminó la materia Base de Datos', registro.accion)
        self.assertIn('InscripcionFinal', registro.valor_anterior)
        self.assertIn('MesaFinal', registro.valor_anterior)
        self.assertEqual(registro.autor_dni, '30666777')

    def test_eliminar_materias_seleccionadas_deja_registro(self):
        self.client.force_login(self.directivo)
        self.client.post('/materias/eliminar_seleccionadas/', {'materia_ids': [self.materia.pk]})
        registro = self.ultimo()
        self.assertIn('Eliminó 1 materia(s): Base de Datos', registro.accion)
        self.assertIn('usuarios_materia', registro.valor_anterior)

    def test_eliminar_mesas_seleccionadas_deja_registro(self):
        self.client.force_login(self.preceptor)
        self.client.post('/mesas/eliminar_seleccionadas/', {'mesa_ids': [self.mesa.pk]})
        registro = self.ultimo()
        self.assertIn('Eliminó 1 mesa(s)', registro.accion)
        self.assertIn('InscripcionFinal', registro.valor_anterior)

    def test_eliminar_una_mesa_deja_registro(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/delete_mesa/{self.mesa.pk}')
        self.assertFalse(MesaFinal.objects.filter(pk=self.mesa.pk).exists())
        self.assertIn('Eliminó', self.ultimo().accion)
        self.assertEqual(self.ultimo().modelo_afectado, 'MesaFinal')

    def test_eliminar_una_inscripcion_a_final_guarda_el_resultado_que_tenia(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/eliminar_inscripcion_final/{self.inscripcion.pk}/')
        registro = self.ultimo()
        self.assertIn('Eliminó la inscripción de Estudiante Crit', registro.accion)
        self.assertIn('nota 8', registro.valor_anterior)

    def test_eliminar_un_usuario_deja_registro(self):
        self.client.force_login(self.directivo)
        self.client.post(f'/delete_user/{self.estudiante.pk}')
        self.assertFalse(Usuario.objects.filter(pk=self.estudiante.pk).exists())
        registro = self.ultimo()
        self.assertEqual(registro.modelo_afectado, 'Usuario')
        self.assertIn('InscripcionFinal', registro.valor_anterior)

    def test_editar_notas_guarda_valor_anterior_y_nuevo(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/cargar_nota_cursada/{self.cursada.pk}/', {'nota_cursada': '9', 'nota_final': ''})
        registro = self.ultimo()
        self.assertIn('Editó las notas', registro.accion)
        self.assertIn('nota de cursada 7', registro.valor_anterior)
        self.assertIn('nota de cursada 9', registro.valor_nuevo)

    def test_corregir_un_final_guarda_motivo_y_valores_en_campos_propios(self):
        self.client.force_login(self.preceptor)
        self.client.post(f'/cargar_nota_final/{self.inscripcion.pk}/',
                         {'nota_final': '6', 'motivo_correccion': 'Error de transcripción del acta'})
        registro = self.ultimo()
        # La nota es decimal: según la base se guarda "8" u "8.0".
        self.assertRegex(registro.valor_anterior, r'^nota 8(\.0)?$')
        self.assertRegex(registro.valor_nuevo, r'^nota 6(\.0)?$')
        self.assertEqual(registro.motivo, 'Error de transcripción del acta')


class CargaMasivaDejaRegistroTest(TestCase):
    """La carga masiva por CSV cambiaba notas sin dejar rastro (#271)."""

    @classmethod
    def setUpTestData(cls):
        carrera = Carrera.objects.create(nombre_carrera='Tecnicatura CSV')
        cls.materia = Materia.objects.create(nombre_materia='Algoritmos', carrera=carrera, anio=1)
        cls.directivo = crear_usuario('dir_csv_audit@test.com', 'Directivo', 'Directiva CSV', 31000111)

    def test_cada_nota_que_cambia_y_el_resumen_quedan_registrados(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        alumno = crear_usuario('alumno_csv@test.com', 'Estudiante', 'Alumno CSV', 31000222)
        usuarios_materia.objects.create(usuario=alumno, materia=self.materia, nota_cursada=5)
        contenido = (
            "Correo electrónico,Nombre estudiante,Documento estudiante,Materia,Nota de cursada\n"
            "alumno_csv@test.com,Alumno CSV,31000222,Algoritmos,8\n"
        )
        self.client.force_login(self.directivo)
        self.client.post('/cargaMasivaEstudiantes/', {
            'csv_file': SimpleUploadedFile('notas.csv', contenido.encode('utf-8'), content_type='text/csv')})

        cambio = RegistroAuditoria.objects.get(accion__startswith='Cargó por CSV')
        self.assertIn('nota de cursada 5', cambio.valor_anterior)
        self.assertIn('nota de cursada 8', cambio.valor_nuevo)
        resumen = RegistroAuditoria.objects.get(accion__startswith='Carga masiva de usuarios')
        self.assertIn('notas.csv', resumen.accion)
        self.assertIn('1 fila(s) con notas', resumen.accion)
