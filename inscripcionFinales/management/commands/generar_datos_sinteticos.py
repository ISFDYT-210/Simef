"""
Arma un instituto ficticio para las pruebas de QA (decision log P-09).

Las vistas previas de cada PR no pueden usar datos reales de estudiantes
(Ley 25.326). Este comando llena una base vacía con datos que no son de nadie,
pensados para recorrer los criterios de aceptación del Sprint 3: un usuario de
cada rol, correlativas, mesas abiertas y cerradas con tribunal, y estudiantes
en cada situación de las reglas de finales (habilitado, con una oportunidad
restante, con las tres agotadas, con el final aprobado, recursando).

Solo corre sobre una base sin usuarios, para no mezclarse nunca con datos
reales. Uso:

    python manage.py generar_datos_sinteticos

Las contraseñas son aleatorias y se muestran una sola vez al terminar; cada
cuenta pide cambiarla en el primer ingreso, como en producción.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from inscripcionFinales.models import (
    Carrera,
    InscripcionFinal,
    Instituto,
    Materia,
    MateriaCorrelativa,
    MesaFinal,
    TribunalMesa,
    Usuario,
    generar_password_aleatoria,
    usuarios_materia,
)

# DNIs del rango 99.000.000, que no está asignado a ninguna persona.
DNI_BASE = 99000000

PERSONAL = [
    # (rol, nombre)
    (Usuario.DIRECTIVO, 'Directora De Prueba'),
    (Usuario.SECRETARIO, 'Secretario De Prueba'),
    (Usuario.PRECEPTOR, 'Preceptora De Prueba'),
    (Usuario.PROFESOR, 'Profesor Uno De Prueba'),
    (Usuario.PROFESOR, 'Profesora Dos De Prueba'),
]

# Materias de la carrera: (clave, nombre, año, día, correlativa). Cada una en
# un día distinto, para que el control de superposición de horarios no frene
# las inscripciones de prueba.
MATERIAS = [
    ('prog1', 'Programación I', 1, 'Lunes', None),
    ('mate1', 'Matemática I', 1, 'Martes', None),
    ('ingles1', 'Inglés I', 1, 'Miércoles', None),
    ('prog2', 'Programación II', 2, 'Jueves', 'prog1'),
    ('bd', 'Base de Datos', 2, 'Viernes', 'mate1'),
]

# Cada estudiante es un caso de las reglas de finales.
#   cursadas: {materia: nota_cursada}
#   finales:  [(materia, mesa_pasada, nota o 'ausente')]
ESTUDIANTES = [
    ('Ana Ingresante', 'Recién inscripta: cursa primer año, todavía sin notas.',
     {}, []),
    ('Bruno Habilitado', 'Cursada de Programación I aprobada: puede rendir el final.',
     {'prog1': 7}, []),
    ('Carla Ultima', 'Programación I: un ausente y un desaprobado, le queda una oportunidad.',
     {'prog1': 6}, [('prog1', 0, 'ausente'), ('prog1', 1, 2)]),
    ('Diego Agotado', 'Programación I: tres oportunidades usadas, ya no puede inscribirse.',
     {'prog1': 5}, [('prog1', 0, 'ausente'), ('prog1', 1, 2), ('prog1', 2, 3)]),
    ('Elena Avanzada', 'Final de Programación I aprobado: puede cursar Programación II. '
     'Recursa Matemática I.',
     {'prog1': 8, 'mate1': 2}, [('prog1', 1, 8)]),
    ('Facundo Recursa', 'Cursada de Programación I desaprobada: no puede rendir.',
     {'prog1': 2}, []),
]


class Command(BaseCommand):
    help = 'Llena una base vacía con un instituto ficticio para las pruebas de QA.'

    def handle(self, *args, **options):
        if Usuario.objects.exists():
            raise CommandError(
                'La base ya tiene usuarios. Este comando solo corre sobre una base '
                'vacía, para no mezclar datos sintéticos con datos reales.'
            )
        with transaction.atomic():
            credenciales = self._generar()

        self.stdout.write(self.style.SUCCESS('Datos sintéticos creados.'))
        self.stdout.write('')
        self.stdout.write('Cuentas (las contraseñas no se vuelven a mostrar):')
        for dni, rol, nombre, password, caso in credenciales:
            self.stdout.write(f'  {dni}  {password}  {rol:<10}  {nombre}')
            if caso:
                self.stdout.write(f'      {caso}')

    def _generar(self):
        ahora = timezone.now()
        credenciales = []
        dnis = iter(range(DNI_BASE + 1, DNI_BASE + 1000))

        def crear_usuario(rol, nombre, caso=''):
            dni = str(next(dnis))
            password = generar_password_aleatoria()
            usuario = Usuario.objects.create_user(
                dni=dni,
                password=password,
                username=f'prueba{dni}',
                nombre_completo=nombre,
                email=f'prueba{dni}@example.com',
                rol=rol,
            )
            credenciales.append((dni, rol, nombre, password, caso))
            return usuario

        instituto = Instituto.objects.create(
            nombre_instituto='Instituto De Prueba',
            email_instituto='instituto@example.com',
            direccion='Calle Falsa 123',
            localidad='Localidad De Prueba',
            ciudad='Ciudad De Prueba',
        )
        carrera = Carrera.objects.create(
            nombre_carrera='Tecnicatura De Prueba',
            num_resolucion='0000/00',
            instituto=instituto,
        )

        personal = [crear_usuario(rol, nombre) for rol, nombre in PERSONAL]
        profesores = [u for u in personal if u.rol == Usuario.PROFESOR]

        materias = {}
        for clave, nombre, anio, dia, _ in MATERIAS:
            materias[clave] = Materia.objects.create(
                nombre_materia=nombre,
                carrera=carrera,
                profesor=profesores[len(materias) % len(profesores)],
                anio=anio,
                dia=dia,
                inscripcionAbierta=True,
            )
        for clave, _, _, _, correlativa in MATERIAS:
            if correlativa:
                MateriaCorrelativa.objects.create(
                    materia=materias[clave], materia_correlativa=materias[correlativa])

        def crear_mesa(materia, llamado, abierta, acta=''):
            mesa = MesaFinal.objects.create(
                materia=materia,
                llamado=llamado,
                vigente=llamado > ahora,
                inscripcionAbierta=abierta,
                aula='Aula 1',
                sede='SEDE LA PLATA',
                numero_acta=acta,
                folio=acta and '1',
            )
            TribunalMesa.objects.create(mesa=mesa, docente=profesores[0], rol=TribunalMesa.PRESIDENTE)
            TribunalMesa.objects.create(mesa=mesa, docente=profesores[1], rol=TribunalMesa.VOCAL)
            return mesa

        # Tres llamados ya rendidos de Programación I, con su acta cargada.
        mesas_pasadas = [
            crear_mesa(materias['prog1'], ahora - timedelta(days=dias), False, acta=f'PRUEBA-{n}')
            for n, dias in enumerate((150, 90, 30), start=1)
        ]
        # Una mesa abierta y otra todavía sin habilitar (para ver el motivo de rechazo).
        crear_mesa(materias['prog1'], ahora + timedelta(days=15), True)
        crear_mesa(materias['mate1'], ahora + timedelta(days=20), False)

        hace_un_anio = ahora - timedelta(days=365)
        for nombre, caso, cursadas, finales in ESTUDIANTES:
            estudiante = crear_usuario(Usuario.ESTUDIANTE, nombre, caso)
            # Al sumarle la carrera, el sistema lo anota solo en las materias
            # de primer año (ver inscribir_en_primer_anio).
            estudiante.carrera.add(carrera)

            for clave, nota in cursadas.items():
                cursada = usuarios_materia.objects.get(usuario=estudiante, materia=materias[clave])
                cursada.nota_cursada = nota
                cursada.modalidad = 'Regular'
                cursada.ciclo_lectivo = str(hace_un_anio.year)
                cursada.save()

            for clave, indice_mesa, resultado in finales:
                ausente = resultado == 'ausente'
                nota = None if ausente else resultado
                InscripcionFinal.objects.create(
                    usuario=estudiante,
                    llamado=mesas_pasadas[indice_mesa],
                    ausente=ausente,
                    nota=nota,
                    aprobada=None if ausente else nota >= 4,
                )
                if nota is not None and nota >= 4:
                    cursada = usuarios_materia.objects.get(usuario=estudiante, materia=materias[clave])
                    cursada.nota_final = nota
                    cursada.aprobada = True
                    cursada.save()

            # La cursada empezó hace un año: así los finales de arriba caen
            # dentro del ciclo actual y cuentan para el tope de oportunidades.
            usuarios_materia.objects.filter(usuario=estudiante).update(ciclo_actual_desde=hace_un_anio)

        return credenciales
