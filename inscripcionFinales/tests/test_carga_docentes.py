"""
Tests de la carga masiva de docentes (#285).

- Un docente nunca queda inscripto como estudiante: para él, Materia es la materia
  que dicta, y se completa Materia.profesor.
- Se acepta la planilla de la institución: Nombre y Apellido, DNI, mail, Carrera,
  Año y Materia, separada por punto y coma, una fila por materia y el nombre vacío
  en las filas siguientes del mismo docente.
- Sin columna Rol, se usa el rol elegido al subir el archivo (por defecto, Estudiante).
- El resultado dice qué docentes quedaron sin materias y qué materias o carreras no están.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from inscripcionFinales.models import Carrera, Materia, RegistroAuditoria, Usuario, usuarios_materia
from inscripcionFinales.tests.test_views import crear_usuario

PLANILLA_INSTITUCION = (
    "Nombre y Apellido;DNI;mail;Carrera;Año;Materia\n"
    "Ana Docente;20.111.222;ana@test.com;Profesorado de Matemática;1;Álgebra I\n"
    ";;;Profesorado de Matemática;2;Geometría\n"
    "Beto Docente;20333444;beto@test.com;Profesorado de Matemática;1;algebra i\n"
)


class CargaMasivaDocentesTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.directivo = crear_usuario('dir_docentes@test.com', 'Directivo', 'Directiva', 20000001)
        cls.mate = Carrera.objects.create(nombre_carrera='Profesorado de Matemática')
        cls.otra = Carrera.objects.create(nombre_carrera='Tecnicatura en Sistemas')
        cls.algebra = Materia.objects.create(nombre_materia='Álgebra I', carrera=cls.mate, anio=1)
        cls.geometria = Materia.objects.create(nombre_materia='Geometría', carrera=cls.mate, anio=2)

    def setUp(self):
        self.client.force_login(self.directivo)

    def subir(self, contenido, rol_por_defecto=None):
        datos = {'csv_file': SimpleUploadedFile('docentes.csv', contenido.encode('utf-8'), content_type='text/csv')}
        if rol_por_defecto:
            datos['rol_por_defecto'] = rol_por_defecto
        return self.client.post('/cargaMasivaEstudiantes/', datos)

    def test_un_profesor_con_materia_no_queda_inscripto_y_pasa_a_dictarla(self):
        respuesta = self.subir(
            "Nombre estudiante,Documento estudiante,Rol,Carrera,Materia\n"
            "Carla Profesora,20555666,Profesor,Profesorado de Matemática,Álgebra I\n"
        )
        carla = Usuario.objects.get(dni='20555666')
        self.assertEqual(carla.rol, Usuario.PROFESOR)
        self.assertFalse(usuarios_materia.objects.filter(usuario=carla).exists())
        self.algebra.refresh_from_db()
        self.assertEqual(self.algebra.profesor, carla)
        self.assertContains(respuesta, '1 materia(s) asignada(s) a docentes')
        registro = RegistroAuditoria.objects.get(accion__startswith='Asignó a Carla Profesora como profesor')
        self.assertEqual((registro.valor_anterior, registro.valor_nuevo),
                         ('Sin profesor', 'Carla Profesora (DNI 20555666)'))

    def test_acepta_la_planilla_de_la_institucion_eligiendo_profesor(self):
        respuesta = self.subir(PLANILLA_INSTITUCION, rol_por_defecto='Profesor')
        ana = Usuario.objects.get(dni='20111222')
        self.assertEqual((ana.nombre_completo, ana.email, ana.rol),
                         ('Ana Docente', 'ana@test.com', Usuario.PROFESOR))
        self.algebra.refresh_from_db()
        self.geometria.refresh_from_db()
        # La fila sin nombre es de Ana: Geometría le queda a ella
        self.assertEqual(self.geometria.profesor, ana)
        self.assertEqual(self.algebra.profesor, ana)
        self.assertEqual(Usuario.objects.filter(rol=Usuario.PROFESOR).count(), 2)
        self.assertFalse(usuarios_materia.objects.filter(usuario__rol=Usuario.PROFESOR).exists())
        self.assertEqual(respuesta.context['usuarios_creados'], 2)
        self.assertEqual(respuesta.context['usuarios_duplicados'], 0)
        # El resumen la muestra una vez, con sus dos materias
        resumen = respuesta.context['resumen_docentes']
        self.assertEqual(len(resumen.materias_por_docente), 2)
        self.assertEqual(resumen.materias_por_docente['20111222'], ('Ana Docente', ['Álgebra I', 'Geometría']))
        # Beto pidió Álgebra I, que ya es de Ana: no se cambia, se avisa, y Beto queda sin materias
        self.assertContains(respuesta, 'Álgebra I: la dicta Ana Docente. No se cambió')
        self.assertIn('Beto Docente (DNI 20333444)', respuesta.context['resumen_docentes'].sin_materias)

    def test_sin_columna_rol_se_crea_como_estudiante_y_la_pantalla_lo_avisa(self):
        self.assertContains(self.client.get('/cargaMasivaEstudiantes/'),
                            'Si no indicás el Rol, cada usuario se crea con el rol elegido arriba')
        self.subir("Nombre,DNI\nSin Rol,20777888\n")
        self.assertEqual(Usuario.objects.get(dni='20777888').rol, Usuario.ESTUDIANTE)

    def test_carrera_inexistente_crea_igual_al_docente_y_lo_informa(self):
        respuesta = self.subir(
            "Nombre y Apellido;DNI;Carrera;Año;Materia\n"
            "Dora Docente;20999000;Profesorado de Química;1;Química I\n",
            rol_por_defecto='Profesor')
        self.assertTrue(Usuario.objects.filter(dni='20999000', rol=Usuario.PROFESOR).exists())
        resumen = respuesta.context['resumen_docentes']
        self.assertEqual(resumen.carreras_no_encontradas, ['Profesorado de Química'])
        self.assertEqual(resumen.sin_materias, ['Dora Docente (DNI 20999000)'])
        self.assertContains(respuesta, 'Carreras que no existen en el sistema')

    def test_materia_que_no_existe_se_informa(self):
        respuesta = self.subir(
            "Nombre y Apellido;DNI;Carrera;Año;Materia\n"
            "Eva Docente;21000111;Profesorado de Matemática;3;Análisis III\n",
            rol_por_defecto='Profesor')
        resumen = respuesta.context['resumen_docentes']
        self.assertEqual(len(resumen.no_encontradas), 1)
        self.assertIn('Análisis III (de Profesorado de Matemática, 3° año): no existe', resumen.no_encontradas[0])

    def test_el_anio_desempata_materias_con_el_mismo_nombre(self):
        ingles_1 = Materia.objects.create(nombre_materia='Inglés', carrera=self.otra, anio=1)
        ingles_2 = Materia.objects.create(nombre_materia='Inglés', carrera=self.otra, anio=2)
        respuesta = self.subir(
            "Nombre y Apellido;DNI;Carrera;Año;Materia\n"
            "Fede Docente;21222333;Tecnicatura en Sistemas;2°;INGLES\n"
            "Gabi Docente;21444555;Tecnicatura en Sistemas;;Inglés\n",
            rol_por_defecto='Profesor')
        ingles_1.refresh_from_db()
        ingles_2.refresh_from_db()
        self.assertEqual(ingles_2.profesor.dni, '21222333')
        self.assertIsNone(ingles_1.profesor)
        self.assertIn('hay más de una con ese nombre', respuesta.context['resumen_docentes'].no_encontradas[0])

    def test_volver_a_cargar_no_duplica_y_asigna_lo_que_falta(self):
        self.subir("Nombre y Apellido;DNI;Rol\nHugo Docente;21666777;Profesor\n")
        respuesta = self.subir(
            "Nombre y Apellido;DNI;Rol;Carrera;Año;Materia\n"
            "Hugo Docente;21666777;Profesor;Profesorado de Matemática;2;Geometría\n"
            ";;Profesor;Profesorado de Matemática;1;Álgebra I\n")
        self.assertEqual(Usuario.objects.filter(dni='21666777').count(), 1)
        self.assertEqual(respuesta.context['usuarios_duplicados'], 1)
        self.geometria.refresh_from_db()
        self.algebra.refresh_from_db()
        self.assertEqual((self.geometria.profesor.dni, self.algebra.profesor.dni), ('21666777', '21666777'))

    def test_un_estudiante_existente_no_pasa_a_dictar_materias(self):
        alumna = crear_usuario('alumna_doc@test.com', 'Estudiante', 'Alumna', 21888999)
        respuesta = self.subir(
            "Nombre y Apellido;DNI;Carrera;Año;Materia\nAlumna;21888999;Profesorado de Matemática;1;Álgebra I\n",
            rol_por_defecto='Profesor')
        self.algebra.refresh_from_db()
        self.assertIsNone(self.algebra.profesor)
        self.assertContains(respuesta, 'ya está cargado como Estudiante y la fila es de Profesor/a')
        alumna.refresh_from_db()
        self.assertEqual(alumna.rol, Usuario.ESTUDIANTE)

    def test_un_docente_existente_no_queda_inscripto_por_una_fila_de_estudiante(self):
        """Antes, una fila con Materia y sin Rol inscribía como estudiante a quien ya era docente."""
        docente = crear_usuario('ya_docente@test.com', 'Profesor', 'Ya Docente', 22000111)
        respuesta = self.subir("Nombre,DNI,Materia,Nota de cursada\nYa Docente,22000111,Álgebra I,8\n")
        self.assertFalse(usuarios_materia.objects.filter(usuario=docente).exists())
        self.assertContains(respuesta, 'ya está cargado como Profesor/a y la fila es de Estudiante')

    def test_otro_rol_con_materia_se_crea_pero_no_se_inscribe(self):
        respuesta = self.subir("Nombre,DNI,Rol,Materia\nPedro Preceptor,22333444,Preceptor,Álgebra I\n")
        preceptor = Usuario.objects.get(dni='22333444')
        self.assertFalse(usuarios_materia.objects.filter(usuario=preceptor).exists())
        self.assertContains(respuesta, 'se ignoró la Materia')

    def test_columnas_sin_acentos_ni_mayusculas_exactas(self):
        """'Teléfono 1' (como figura en la pantalla) antes se ignoraba: el código leía 'Telefono 1'."""
        self.subir("NOMBRE,documento,Teléfono 1\nIris Alumna,22555666,2211234567\n")
        self.assertEqual(Usuario.objects.get(dni='22555666').telefono_1, '2211234567')
