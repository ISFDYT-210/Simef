"""
Constancia académica del estudiante en PDF, generada dentro del sistema.

Antes, la vista reporte_estudiante_descarga mandaba el HTML de la constancia
(nombre, DNI y todas las notas del estudiante) a un servicio externo
(api.html2pdf.app) para convertirlo en PDF, sin contrato ni clave (SEC-08 de la
auditoría de seguridad). La Ley 25.326 regula esa cesión de datos personales a
terceros. Este módulo arma el mismo documento con reportlab, que ya se usa para
el listado de mesas, así que los datos no salen del sistema.

Recibe el contexto de views.obtener_contexto_reporte y devuelve los bytes del PDF.
"""
import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ENCABEZADO = Path(__file__).resolve().parent / 'static' / 'img' / 'encabezado_constancia.png'

TINTA = colors.HexColor('#14304D')
GRIS = colors.HexColor('#5B7590')
FONDO = colors.HexColor('#EEF3F8')

_base = ParagraphStyle('base', fontName='Helvetica', fontSize=10, leading=14, textColor=colors.black)
ESTILOS = {
    'institucion': ParagraphStyle('institucion', parent=_base, fontName='Helvetica-Bold',
                                  fontSize=10, alignment=TA_CENTER, leading=13),
    'titulo': ParagraphStyle('titulo', parent=_base, fontName='Helvetica-Bold', fontSize=11,
                             alignment=TA_CENTER, leading=15, spaceBefore=10, spaceAfter=10,
                             textColor=TINTA),
    'cuerpo': ParagraphStyle('cuerpo', parent=_base, alignment=TA_JUSTIFY, leading=16),
    'celda': ParagraphStyle('celda', parent=_base, fontSize=8.5, leading=10.5),
    'celda_centro': ParagraphStyle('celda_centro', parent=_base, fontSize=8.5, leading=10.5,
                                   alignment=TA_CENTER),
    'firma': ParagraphStyle('firma', parent=_base, fontSize=9, alignment=TA_CENTER,
                            textColor=GRIS),
}


def _texto(valor, defecto='-'):
    """Escapa datos que vienen de la base: Paragraph interpreta marcado."""
    if valor is None or valor == '':
        return defecto
    return escape(str(valor))


def _nombre_anio(anio):
    return {1: '1er Año', 2: '2do Año', 3: '3er Año'}.get(anio, f'{anio}º Año')


def _tabla_anio(anio, materias):
    e = ESTILOS
    encabezado = [
        [Paragraph('<b>Curso</b>', e['celda_centro']), Paragraph('<b>Asignaturas</b>', e['celda']),
         Paragraph('<b>Calificación</b>', e['celda_centro']), '',
         Paragraph('<b>Fecha</b>', e['celda_centro'])],
        ['', '', Paragraph('<b>En Nº</b>', e['celda_centro']),
         Paragraph('<b>En Letras</b>', e['celda_centro']), ''],
    ]
    filas = []
    for i, materia in enumerate(materias):
        filas.append([
            Paragraph(_nombre_anio(anio), e['celda_centro']) if i == 0 else '',
            Paragraph(_texto(materia['nombre']), e['celda']),
            Paragraph(_texto(materia['nota_cursada']), e['celda_centro']),
            Paragraph(_texto(materia['calif_cursada']), e['celda_centro']),
            Paragraph(_texto(materia['fecha']), e['celda_centro']),
        ])
    tabla = Table(encabezado + filas, colWidths=[2.2 * cm, 8.3 * cm, 1.6 * cm, 2.4 * cm, 2.5 * cm],
                  repeatRows=2)
    estilo = [
        ('GRID', (0, 0), (-1, -1), 0.5, GRIS),
        ('BACKGROUND', (0, 0), (-1, 1), FONDO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (3, 0)), ('SPAN', (4, 0), (4, 1)),
    ]
    if filas:
        estilo.append(('SPAN', (0, 2), (0, len(filas) + 1)))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def generar_constancia_pdf(contexto):
    """Arma la constancia con el contexto de obtener_contexto_reporte y devuelve bytes."""
    usuario = contexto['usuario']
    e = ESTILOS
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title='Constancia académica', author='ISFDyT Nº 210',
    )
    elementos = []

    if ENCABEZADO.exists():
        logo = Image(str(ENCABEZADO), width=8.4 * cm, height=2.0 * cm)
        logo.hAlign = 'LEFT'
        elementos += [logo, Spacer(1, 0.3 * cm)]

    elementos += [
        Paragraph('DIRECCIÓN DE EDUCACIÓN SUPERIOR', e['institucion']),
        Paragraph('INSTITUTO SUPERIOR DE FORMACIÓN DOCENTE Y TÉCNICA Nº 210', e['institucion']),
        Paragraph('CONSTANCIA DEL PORCENTAJE DE PERSPECTIVAS, ESPACIOS Y ÁREAS DE CONOCIMIENTO '
                  'APROBADAS (A LA FECHA)', e['titulo']),
    ]

    nombre = _texto((usuario.nombre_completo or '').upper(), '___________________')
    dni = _texto(usuario.dni, '_____________')
    carrera = _texto((contexto.get('nombre_carrera') or '').upper(), '___________________')
    resolucion = contexto.get('resolucion_carrera')
    resolucion = f' (Resolución Nº {_texto(resolucion)})' if resolucion else ''
    elementos.append(Paragraph(
        f'Se deja constancia que el/la estudiante <b>{nombre}</b>, DNI: <b>{dni}</b>, alumno regular '
        f'de este establecimiento en la <b>{carrera}</b>{resolucion} y las asignaturas de '
        'Perspectivas, Espacios y Áreas del plan de estudios, cuyo detalle figura al pie, que '
        f'realizan el <b>{_texto(contexto.get("porcentaje_aprobadas"), "0")}%</b> '
        f'{_texto(contexto.get("porcentaje_en_letras"), "")} expresado en Perspectivas, Espacios '
        'y Áreas del plan de estudios.',
        e['cuerpo'],
    ))
    elementos.append(Spacer(1, 0.4 * cm))

    for anio, materias in contexto.get('materias_por_anio', {}).items():
        elementos += [_tabla_anio(anio, materias), Spacer(1, 0.3 * cm)]

    cierre = Paragraph(
        'A pedido del interesado y al solo efecto de ser presentado ante las autoridades que '
        'estime corresponder, se extiende la presente constancia, en la ciudad de La Plata en el '
        f'día de hoy {_texto(contexto.get("fecha_actual"))}.',
        e['cuerpo'],
    )
    # Tres columnas: las dos firmas con un espacio en el medio, para que cada una
    # tenga su propia línea.
    firmas = Table(
        [['', '', ''], [Paragraph('Sello del establecimiento', e['firma']), '',
                        Paragraph('Firma y sello aclaratorio', e['firma'])]],
        colWidths=[7 * cm, 3 * cm, 7 * cm], rowHeights=[2.2 * cm, None],
    )
    firmas.setStyle(TableStyle([
        ('LINEABOVE', (0, 1), (0, 1), 0.5, GRIS), ('LINEABOVE', (2, 1), (2, 1), 0.5, GRIS),
    ]))
    # El cierre y las firmas van juntos: nunca quedan en páginas distintas.
    elementos.append(KeepTogether([cierre, Spacer(1, 0.6 * cm), firmas]))

    doc.build(elementos)
    return buffer.getvalue()
