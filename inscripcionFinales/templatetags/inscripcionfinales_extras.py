from django import template
import datetime

register = template.Library()


@register.filter
def resumen_anio(materias):
    """
    Recibe la lista de materias de un año (tal como vienen en el dict
    materias_por_anio del contexto: cada item con 'nombre', 'nota_cursada',
    'nota_final', 'calif_cursada', 'calif_final', 'fecha') y devuelve un
    dict con:
      - plan: cantidad total de materias del plan para ese año
      - rendidas: cuántas ya tienen nota_final cargada (aprobada o no)
      - faltan: plan - rendidas
    """
    if not materias:
        return {'plan': 0, 'rendidas': 0, 'faltan': 0}

    plan = len(materias)
    rendidas = sum(
        1 for m in materias
        if m.get('nota_final') not in (None, '-', '', 'None', 'none')
    )
    faltan = plan - rendidas

    return {'plan': plan, 'rendidas': rendidas, 'faltan': faltan}


@register.filter
def restar(value, arg):
    """Resta arg a value, tolerando que lleguen como string."""
    try:
        return int(value) - int(arg)
    except (TypeError, ValueError):
        try:
            return float(value) - float(arg)
        except (TypeError, ValueError):
            return ''


@register.filter
def fecha_larga(value):
    """
    Convierte una fecha a texto largo en español.
    Acepta un string 'dd/mm/aaaa' (formato que usa obtener_contexto_reporte
    para fecha_actual), 'aaaa-mm-dd', o un objeto date/datetime.
    Ej: '09/09/2026' -> '09 de septiembre de 2026'
    """
    meses = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]

    dt = None
    if isinstance(value, (datetime.date, datetime.datetime)):
        dt = value
    elif isinstance(value, str):
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                dt = datetime.datetime.strptime(value, fmt)
                break
            except ValueError:
                continue

    if dt is None:
        return value

    return f"{dt.day:02d} de {meses[dt.month - 1]} de {dt.year}"
