from django import template

register = template.Library()


@register.filter
def concatenate(arg1, arg2):
    return str(arg1) + str(arg2)


def _esta_aprobada(m):
    """Una materia cuenta como rendida/aprobada si el backend marcó 'aprobada'
    o, en su defecto, si tiene una nota de cursada válida (no vacía / no '-')."""
    if isinstance(m, dict):
        if m.get('aprobada') is not None:
            return bool(m.get('aprobada'))
        nota = m.get('nota_cursada')
    else:
        nota = getattr(m, 'nota_cursada', None)
    return str(nota).strip() not in ('', '-', 'None', 'none', 'None')


@register.filter
def resumen_anio(materias):
    """Devuelve {plan, rendidas, faltan} para una lista de materias de un año."""
    materias = list(materias or [])
    plan = len(materias)
    rendidas = sum(1 for m in materias if _esta_aprobada(m))
    return {'plan': plan, 'rendidas': rendidas, 'faltan': plan - rendidas}


@register.filter
def restar(a, b):
    try:
        return int(a) - int(b)
    except (TypeError, ValueError):
        return ''


_MESES = ['enero','febrero','marzo','abril','mayo','junio','julio',
          'agosto','septiembre','octubre','noviembre','diciembre']


@register.filter
def fecha_larga(fecha_str):
    """'31/07/2026' -> 'a los 31 días del mes de julio de 2026'."""
    try:
        d, m, y = str(fecha_str).split('/')
        return 'a los %d días del mes de %s de %s' % (int(d), _MESES[int(m)-1], y)
    except Exception:
        return str(fecha_str)
