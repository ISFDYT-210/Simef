"""
La inscripción del alumno a cursadas aplica en el servidor las mismas reglas que
muestra la pantalla "Inscripción a materias" (#288): materia de su carrera, de
alta, con la inscripción abierta y las correlativas cumplidas, y una modalidad
permitida (Regular, o Libre si no es una práctica).
"""
from django.test import TestCase

from inscripcionFinales import correlativas
from inscripcionFinales.models import Carrera, Materia, MateriaCorrelativa, usuarios_materia
from inscripcionFinales.tests.test_views import crear_usuario


class InscripcionCursadasTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.mia = Carrera.objects.create(nombre_carrera='Profesorado de Primaria')
        cls.otra = Carrera.objects.create(nombre_carrera='Tecnicatura en Sistemas')
        cls.alumno = crear_usuario('alu_288@test.com', 'Estudiante', 'Alumno', 42000001)
        cls.alumno.carrera.add(cls.mia)
        # Ingresante: las materias de primer año le quedan disponibles
        usuarios_materia.objects.create(
            usuario=cls.alumno, materia=Materia.objects.create(nombre_materia='Base', carrera=cls.mia, anio=1),
            nota_cursada=8)
        cls.abierta = Materia.objects.create(nombre_materia='Didáctica', carrera=cls.mia, anio=1, inscripcionAbierta=True)
        cls.practica = Materia.objects.create(nombre_materia='Práctica Docente I', carrera=cls.mia, anio=1,
                                              inscripcionAbierta=True)

    def setUp(self):
        self.client.force_login(self.alumno)

    def inscribir(self, materia, modalidad):
        self.client.post(f'/inscribirse_materia/{materia.pk}/{modalidad}')
        return usuarios_materia.objects.filter(usuario=self.alumno, materia=materia).first()

    def test_regular_y_libre_en_una_materia_disponible(self):
        self.assertEqual(self.inscribir(self.abierta, 'Libre').modalidad, 'Libre')
        self.assertEqual(self.inscribir(self.practica, 'Regular').modalidad, 'Regular')

    def test_una_practica_no_se_cursa_libre(self):
        self.assertIsNone(self.inscribir(self.practica, 'Libre'))

    def test_modalidad_que_no_ofrece_la_pantalla(self):
        self.assertIsNone(self.inscribir(self.abierta, 'Itinerante'))
        self.assertIsNone(self.inscribir(self.abierta, 'Cualquiera'))

    def test_inscripcion_cerrada(self):
        cerrada = Materia.objects.create(nombre_materia='Cerrada', carrera=self.mia, anio=1)
        self.assertIsNone(self.inscribir(cerrada, 'Regular'))

    def test_materia_de_otra_carrera(self):
        ajena = Materia.objects.create(nombre_materia='Ajena', carrera=self.otra, anio=1, inscripcionAbierta=True)
        self.assertIsNone(self.inscribir(ajena, 'Libre'))

    def test_materia_dada_de_baja(self):
        baja = Materia.objects.create(nombre_materia='Vieja', carrera=self.mia, anio=1, inscripcionAbierta=True,
                                      activo=False)
        self.assertIsNone(self.inscribir(baja, 'Regular'))

    def test_correlativas_sin_cumplir(self):
        previa = Materia.objects.create(nombre_materia='Previa', carrera=self.mia, anio=2)
        con_previa = Materia.objects.create(nombre_materia='Con previa', carrera=self.mia, anio=3, inscripcionAbierta=True)
        MateriaCorrelativa.objects.create(materia=con_previa, materia_correlativa=previa)
        self.assertIsNone(self.inscribir(con_previa, 'Libre'))

    def test_la_pantalla_y_el_servidor_usan_la_misma_regla_de_practicas(self):
        self.assertTrue(correlativas.es_practica(self.practica))
        self.assertTrue(correlativas.es_practica(Materia(nombre_materia='PRACTICA PROFESIONAL')))
        self.assertFalse(correlativas.es_practica(self.abierta))
        respuesta = self.client.get('/inscripcionMateriaEst/')
        self.assertContains(respuesta, 'data-practica="1"')
