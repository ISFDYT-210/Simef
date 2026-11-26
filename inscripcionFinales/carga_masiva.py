"""Lectura de la planilla de carga masiva de usuarios, y asignación de materias a docentes (#285).

La carga masiva nació para estudiantes. Para cargar la planta docente hacía falta:
- aceptar los encabezados de la planilla de la institución (Nombre y Apellido, DNI,
  mail, Año), sin acentos ni mayúsculas exactas, y separada por comas o por punto y
  coma, como la guarda Excel en castellano;
- no inscribir nunca a un docente como estudiante: para un docente, Materia es la
  materia que dicta, y se completa Materia.profesor;
- aceptar una fila por materia, con el nombre vacío en las filas siguientes del
  mismo docente;
- informar qué docentes quedaron sin materias y qué materias o carreras no están.
"""
import re
import unicodedata

from .audit import registrar_auditoria
from .models import Carrera, Materia, Usuario


def clave(texto):
    """'  Matemática   I ' -> 'matematica i': para comparar sin acentos, mayúsculas ni espacios de más."""
    sin_tildes = unicodedata.normalize('NFD', str(texto or '').replace('﻿', ''))
    sin_tildes = ''.join(c for c in sin_tildes if unicodedata.category(c) != 'Mn')
    return ' '.join(sin_tildes.lower().split())


# Nombre de columna que usa la carga -> otros nombres con que puede venir. Además, cualquier
# columna se reconoce sin importar acentos ni mayúsculas ("Telefono 1" = "Teléfono 1").
SINONIMOS = {
    'Nombre estudiante': ('nombre', 'nombre y apellido', 'apellido y nombre', 'nombre completo', 'docente'),
    'Documento estudiante': ('documento', 'dni', 'numero de documento', 'nro de documento', 'nro documento'),
    'Correo electrónico': ('correo', 'mail', 'email', 'e-mail'),
    'Año': ('anio',),
    'Apellido': ('apellidos',),
}
COLUMNAS = (
    'Nombre estudiante', 'Documento estudiante', 'Correo electrónico', 'Apellido', 'Username',
    'Fecha nacimiento', 'Direccion', 'Localidad', 'Ciudad', 'Nacionalidad', 'Telefono 1', 'Telefono 2',
    'Estado civil', 'Sexo', 'Rol', 'Carrera', 'Año', 'Materia', 'Modalidad', 'Nota de cursada',
    'Nota de final', 'Matricula', 'Especialidad', 'Cargo', 'Area',
)
_CANONICA = {clave(c): c for c in COLUMNAS}
for _canonica, _otros in SINONIMOS.items():
    _CANONICA.update({clave(o): _canonica for o in _otros})


def normalizar_encabezados(encabezados):
    """Lleva cada encabezado al nombre que usa la carga. Los que no conoce quedan como vienen."""
    return [_CANONICA.get(clave(e), (e or '').strip()) for e in (encabezados or [])]


def detectar_delimitador(primera_linea):
    """Excel en castellano guarda el CSV separado por punto y coma."""
    return ';' if primera_linea.count(';') > primera_linea.count(',') else ','


def rol_canonico(texto):
    """'PROFESOR', 'profesor' -> 'Profesor'. None si no es un rol del sistema."""
    return next((r for r, _ in Usuario.ROL_CHOICES if r.lower() == (texto or '').strip().lower()), None)


def leer_anio(texto):
    """'2', '2°', '2º año' -> 2. None si no trae un número."""
    numero = re.search(r'\d+', texto or '')
    return int(numero.group()) if numero else None


def buscar_carrera(nombre):
    objetivo = clave(nombre)
    return next((c for c in Carrera.objects.all() if clave(c.nombre_carrera) == objetivo), None)


def buscar_materia(nombre, carrera=None, anio=None):
    """La materia de alta con ese nombre (sin importar acentos ni mayúsculas), en esa
    carrera y año si vienen. Devuelve (materia, None) o (None, motivo)."""
    materias = Materia.objects.de_alta().select_related('carrera')
    if carrera is not None:
        materias = materias.filter(carrera=carrera)
    if anio is not None:
        materias = materias.filter(anio=anio)
    objetivo = clave(nombre)
    candidatas = [m for m in materias if clave(m.nombre_materia) == objetivo]
    if len(candidatas) == 1:
        return candidatas[0], None
    if candidatas:
        return None, 'hay más de una con ese nombre: indicá la Carrera y el Año'
    return None, 'no existe'


class ResumenDocentes:
    """Lo que la carga hizo con los docentes, para mostrarlo al terminar."""

    def __init__(self):
        self.materias_por_docente = {}   # dni -> (nombre, [materias asignadas o que ya dictaba])
        self.asignadas = 0
        self.no_encontradas = []
        self.carreras_no_encontradas = []
        self.con_otro_profesor = []

    def registrar(self, docente):
        # str(): recién creado, el DNI del objeto es el número que se le pasó;
        # leído de la base, es texto. Tiene que ser la misma clave.
        self.materias_por_docente.setdefault(str(docente.dni), (str(docente), []))

    def anotar(self, lista, texto):
        if texto not in lista:
            lista.append(texto)

    @property
    def sin_materias(self):
        return [f'{nombre} (DNI {dni})' for dni, (nombre, materias) in self.materias_por_docente.items()
                if not materias]

    @property
    def hay_docentes(self):
        return bool(self.materias_por_docente)

    @property
    def hay_avisos(self):
        return bool(self.sin_materias or self.no_encontradas or self.carreras_no_encontradas
                    or self.con_otro_profesor)


def asignar_materia(request, docente, fila, numero_fila, resumen):
    """Para un docente, la columna Materia es la materia que dicta: completa Materia.profesor.
    Nunca crea una inscripción de estudiante (#285)."""
    resumen.registrar(docente)
    nombre_materia = (fila.get('Materia') or '').strip()
    if not nombre_materia:
        return

    carrera = None
    nombre_carrera = (fila.get('Carrera') or '').strip()
    if nombre_carrera:
        carrera = buscar_carrera(nombre_carrera)
        if carrera is None:
            resumen.anotar(resumen.carreras_no_encontradas, nombre_carrera)
            resumen.anotar(resumen.no_encontradas,
                           f'Fila {numero_fila}: {nombre_materia}, de {nombre_carrera} (la carrera no existe)')
            return
    anio = leer_anio(fila.get('Año'))

    materia, motivo = buscar_materia(nombre_materia, carrera, anio)
    if materia is None:
        donde = ', '.join(filter(None, [f'de {carrera}' if carrera else '', f'{anio}° año' if anio else '']))
        resumen.anotar(resumen.no_encontradas,
                       f'Fila {numero_fila}: {nombre_materia}{f" ({donde})" if donde else ""}: {motivo}')
        return

    _, materias = resumen.materias_por_docente[str(docente.dni)]
    actual = materia.profesor
    if actual is not None and actual.pk != docente.pk and actual.is_active:
        resumen.anotar(resumen.con_otro_profesor,
                       f'{materia}: la dicta {actual}. No se cambió; si corresponde, se cambia desde la materia.')
        return
    if actual is None or actual.pk != docente.pk:
        materia.profesor = docente
        materia.save(update_fields=['profesor'])
        resumen.asignadas += 1
        registrar_auditoria(
            request, f'Asignó a {docente} como profesor de {materia} (carga masiva)', 'Materia', materia.pk,
            valor_anterior=f'{actual} (dado de baja)' if actual else 'Sin profesor',
            valor_nuevo=f'{docente} (DNI {docente.dni})',
        )
    if str(materia) not in materias:
        materias.append(str(materia))
