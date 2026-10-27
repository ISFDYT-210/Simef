"""
Tests del comando generar_datos_sinteticos (P-09).

Además de que el comando corra, se comprueba que cada estudiante ficticio
quede en la situación que dice su caso, usando las mismas funciones que usa
el sistema para decidir si alguien puede cursar o rendir.
"""
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from inscripcionFinales.correlativas import intentos_consumidos, puede_cursar, puede_rendir
from inscripcionFinales.models import EstadoCursada, Materia, MesaFinal, Usuario, usuarios_materia


class DatosSinteticosTest(TestCase):

    def setUp(self):
        self.salida = StringIO()
        call_command('generar_datos_sinteticos', stdout=self.salida)
        self.prog1 = Materia.objects.get(nombre_materia='Programación I')

    def estudiante(self, nombre):
        return Usuario.objects.get(nombre_completo=nombre)

    def test_hay_un_usuario_de_cada_rol(self):
        roles = set(Usuario.objects.values_list('rol', flat=True))
        self.assertEqual(roles, {r for r, _ in Usuario.ROL_CHOICES})

    def test_ningun_dato_parece_real(self):
        for usuario in Usuario.objects.all():
            self.assertTrue(usuario.dni.startswith('99'), usuario.dni)
            self.assertTrue(usuario.email.endswith('@example.com'), usuario.email)
            self.assertTrue(usuario.first_login)

    def test_muestra_las_contrasenas_una_vez_y_sirven(self):
        texto = self.salida.getvalue()
        primera = next(linea.split() for linea in texto.splitlines() if linea.strip().startswith('99'))
        dni, password = primera[0], primera[1]
        self.assertTrue(Usuario.objects.get(dni=dni).check_password(password))

    def test_bruno_puede_rendir(self):
        self.assertEqual(puede_rendir(self.estudiante('Bruno Habilitado').pk, self.prog1.pk), (True, None))

    def test_carla_tiene_una_oportunidad_y_el_ausente_cuenta(self):
        carla = self.estudiante('Carla Ultima')
        self.assertEqual(intentos_consumidos(carla.pk, self.prog1.pk), 3)
        self.assertTrue(puede_rendir(carla.pk, self.prog1.pk)[0])

    def test_diego_agoto_las_cuatro_oportunidades(self):
        puede, motivo = puede_rendir(self.estudiante('Diego Agotado').pk, self.prog1.pk)
        self.assertFalse(puede)
        self.assertIn('oportunidades', motivo)

    def test_elena_aprobo_y_puede_cursar_la_correlativa(self):
        elena = self.estudiante('Elena Avanzada')
        prog2 = Materia.objects.get(nombre_materia='Programación II')
        self.assertIn('final aprobado', puede_rendir(elena.pk, self.prog1.pk)[1])
        self.assertTrue(puede_cursar(elena.pk, prog2.pk)[0])

    def test_facundo_no_puede_rendir(self):
        puede, motivo = puede_rendir(self.estudiante('Facundo Recursa').pk, self.prog1.pk)
        self.assertFalse(puede)
        self.assertIn('cursada aprobada', motivo)

    def test_gabriela_promociono_y_no_rinde_final(self):
        gabriela = self.estudiante('Gabriela Promocionada')
        cursada = usuarios_materia.objects.get(usuario=gabriela, materia=self.prog1)
        self.assertEqual(cursada.estado, EstadoCursada.PROMOCIONADO)
        puede, motivo = puede_rendir(gabriela.pk, self.prog1.pk)
        self.assertFalse(puede)
        self.assertIn('final aprobado', motivo)

    def test_las_mesas_pasadas_tienen_acta_y_folio(self):
        for mesa in MesaFinal.objects.filter(vigente=False):
            self.assertTrue(mesa.numero_acta)
            self.assertTrue(mesa.folio)
            self.assertEqual(mesa.tribunal.filter(activo=True).count(), 2)

    def test_no_corre_sobre_una_base_con_usuarios(self):
        with self.assertRaises(CommandError):
            call_command('generar_datos_sinteticos', stdout=StringIO())
