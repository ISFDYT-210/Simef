"""
Lógica centralizada de correlativas. Reglas confirmadas con el instituto:

- Primer año: el ingresante queda inscripto en bloque y no se evalúa ninguna
  correlativa. Si un alumno de años superiores recursa una materia de primer
  año, se evalúa como cualquier otra materia (sin la regla de bloque).
- Para CURSAR una materia: cursada aprobada de cada una de sus correlativas
  (no hace falta el final).
- Para RENDIR el final de una materia: cursada aprobada de esa misma materia
  + final aprobado de cada una de sus correlativas.
- La promoción cuenta como final aprobado (habilita a cursar y a rendir la
  materia siguiente).

Tanto la vista de inscripción a materias como la de finales deben pasar por
`puede_cursar` / `puede_rendir` en vez de reimplementar la validación.
"""
from .models import (
    EstadoCursada,
    InscripcionFinal,
    Materia,
    MateriaCorrelativa,
    MesaFinal,
    usuarios_materia,
    ESTADOS_CURSADA_APROBADA,
    ESTADOS_FINAL_APROBADO,
)

# RECURSA/ABANDONO no cuentan como "inscripción activa": el alumno tiene que
# poder volver a inscribirse (recursar) en esa materia.
ESTADOS_INACTIVOS = {EstadoCursada.RECURSA, EstadoCursada.ABANDONO}

# Motivo exacto que usa finales_con_requisitos cuando el único problema es la
# ventana de inscripción (y no algo académico): es la señal de que la mesa es
# candidata a inscripción excepcional (ver MesaFinal.inscripcion_excepcional_vigente).
MOTIVO_INSCRIPCION_CERRADA = "La inscripción a esta mesa no está abierta"

# Para decidir, entre varios intentos históricos de la misma materia, cuál
# usar al evaluar correlativas de OTRAS materias: el mejor resultado gana.
_PRIORIDAD_ESTADO = {
    EstadoCursada.APROBADO: 0,
    EstadoCursada.PROMOCIONADO: 1,
    EstadoCursada.REGULAR: 2,
    EstadoCursada.EN_CURSO: 3,
    EstadoCursada.RECURSA: 4,
    EstadoCursada.ABANDONO: 5,
}


def _inscripciones_por_materia(usuario_id, materia_ids):
    """
    Una sola consulta: por cada materia, el mejor intento del usuario (si
    recursó, puede haber más de un registro; para evaluar si es correlativa
    de otra materia interesa el más favorable, no el más reciente).
    """
    mejor_por_materia = {}
    for um in usuarios_materia.objects.filter(usuario_id=usuario_id, materia_id__in=materia_ids):
        actual = mejor_por_materia.get(um.materia_id)
        if actual is None or _PRIORIDAD_ESTADO.get(um.estado, 99) < _PRIORIDAD_ESTADO.get(actual.estado, 99):
            mejor_por_materia[um.materia_id] = um
    return mejor_por_materia


def tiene_inscripcion_activa(usuario_id, materia_id):
    """
    True si ya tiene una cursada en curso o completa de esta materia. Si
    todos sus intentos previos quedaron en RECURSA o ABANDONO, no cuenta
    como activa: puede volver a inscribirse.
    """
    return usuarios_materia.objects.filter(
        usuario_id=usuario_id, materia_id=materia_id
    ).exclude(estado__in=ESTADOS_INACTIVOS).exists()


def tiene_cursada_aprobada(inscripcion):
    """`inscripcion`: instancia de usuarios_materia, o None si nunca la cursó."""
    if inscripcion is None:
        return False
    return inscripcion.modalidad == 'Libre' or inscripcion.estado in ESTADOS_CURSADA_APROBADA


def tiene_final_aprobado(inscripcion):
    if inscripcion is None:
        return False
    return inscripcion.estado in ESTADOS_FINAL_APROBADO


def es_ingresante(usuario_id, carrera_id):
    """
    True si el alumno todavía no avanzó más allá de primer año en esta
    carrera, es decir que la inscripción en bloque sigue siendo lo único que
    tiene (no cursó ninguna materia de años superiores).
    """
    return not usuarios_materia.objects.filter(
        usuario_id=usuario_id, materia__carrera_id=carrera_id
    ).exclude(materia__anio=1).exists()


def puede_cursar(usuario_id, materia_id):
    """Devuelve (puede: bool, motivo: str | None)."""
    materia = Materia.objects.get(id=materia_id)

    if tiene_inscripcion_activa(usuario_id, materia_id):
        return False, f"Ya está inscripto en {materia}"

    if materia.anio == 1 and es_ingresante(usuario_id, materia.carrera_id):
        return True, None

    correlativas = list(
        MateriaCorrelativa.objects.filter(materia_id=materia_id).select_related('materia_correlativa')
    )
    if not correlativas:
        return True, None

    inscripciones = _inscripciones_por_materia(usuario_id, [c.materia_correlativa_id for c in correlativas])
    for correlativa in correlativas:
        inscripcion = inscripciones.get(correlativa.materia_correlativa_id)
        if not tiene_cursada_aprobada(inscripcion):
            return False, f"Falta la cursada aprobada de {correlativa.materia_correlativa}"
    return True, None


def puede_rendir(usuario_id, materia_id):
    """Devuelve (puede: bool, motivo: str | None)."""
    materia = Materia.objects.get(id=materia_id)
    inscripcion_materia = usuarios_materia.objects.filter(usuario_id=usuario_id, materia_id=materia_id).first()

    if not tiene_cursada_aprobada(inscripcion_materia):
        return False, f"Falta la cursada aprobada de {materia}"
    if tiene_final_aprobado(inscripcion_materia):
        return False, f"{materia} ya tiene el final aprobado"

    correlativas = list(
        MateriaCorrelativa.objects.filter(materia_id=materia_id).select_related('materia_correlativa')
    )
    if not correlativas:
        return True, None

    inscripciones = _inscripciones_por_materia(usuario_id, [c.materia_correlativa_id for c in correlativas])
    for correlativa in correlativas:
        inscripcion = inscripciones.get(correlativa.materia_correlativa_id)
        if not tiene_final_aprobado(inscripcion):
            return False, f"Falta el final aprobado de {correlativa.materia_correlativa}"
    return True, None


def _motivo_correlativas_faltantes(faltantes):
    nombres = ', '.join(str(m) for m in faltantes)
    if len(faltantes) == 1:
        return f"Falta la cursada aprobada de {nombres}"
    return f"Faltan las cursadas aprobadas de {nombres}"


def materias_con_requisitos(usuario):
    """
    Todas las materias con inscripción abierta de las carreras del alumno que
    todavía no cursó (ni tiene en curso), cada una con si puede inscribirse y
    el motivo puntual si no puede. Pensado para el desglose de requisitos en
    la UI de lista_materias_user, en vez de ocultar sin explicar.

    Trae todo en bloque (inscripciones propias, correlativas, estado de
    ingresante por carrera) para no repetir el N+1 que ya daba timeout contra
    Neon.
    """
    materias = Materia.objects.filter(inscripcionAbierta=True, carrera__in=usuario.carrera.all())
    materia_ids = [m.id for m in materias]

    inscripciones_usuario = {}  # materia_id -> mejor intento (para evaluar correlativas de otras materias)
    materias_con_inscripcion_activa = set()
    for um in usuarios_materia.objects.filter(usuario_id=usuario.id):
        if um.estado not in ESTADOS_INACTIVOS:
            materias_con_inscripcion_activa.add(um.materia_id)
        actual = inscripciones_usuario.get(um.materia_id)
        if actual is None or _PRIORIDAD_ESTADO.get(um.estado, 99) < _PRIORIDAD_ESTADO.get(actual.estado, 99):
            inscripciones_usuario[um.materia_id] = um

    correlativas_por_materia = {}
    for c in MateriaCorrelativa.objects.filter(materia_id__in=materia_ids).select_related('materia_correlativa'):
        correlativas_por_materia.setdefault(c.materia_id, []).append(c)

    carreras_primer_anio = {m.carrera_id for m in materias if m.anio == 1}
    ingresante_por_carrera = {
        carrera_id: es_ingresante(usuario.id, carrera_id) for carrera_id in carreras_primer_anio
    }

    resultado = []
    for materia in materias:
        if materia.id in materias_con_inscripcion_activa:
            continue  # cursada en curso o ya completa: no es candidata a "inscribirse"

        if materia.anio == 1 and ingresante_por_carrera.get(materia.carrera_id):
            resultado.append({'materia': materia, 'disponible': True, 'motivo': None})
            continue

        correlativas = correlativas_por_materia.get(materia.id, [])
        faltantes = [
            c.materia_correlativa for c in correlativas
            if not tiene_cursada_aprobada(inscripciones_usuario.get(c.materia_correlativa_id))
        ]
        if faltantes:
            resultado.append({'materia': materia, 'disponible': False, 'motivo': _motivo_correlativas_faltantes(faltantes)})
        else:
            resultado.append({'materia': materia, 'disponible': True, 'motivo': None})

    return resultado


def materias_disponibles_para_cursar(usuario):
    """Atajo sobre materias_con_requisitos: solo las que el alumno ya puede cursar."""
    return [item['materia'] for item in materias_con_requisitos(usuario) if item['disponible']]


def _motivo_finales_faltantes(faltantes):
    nombres = ', '.join(str(m) for m in faltantes)
    if len(faltantes) == 1:
        return f"Falta el final aprobado de {nombres}"
    return f"Faltan los finales aprobados de {nombres}"


def finales_con_requisitos(usuario):
    """
    Todas las mesas vigentes de materias de las carreras del alumno, cada una
    con si puede inscribirse y el motivo puntual si no. Mismo espíritu que
    materias_con_requisitos: desglose para la UI en vez de ocultar sin explicar.
    """
    mesas = list(
        MesaFinal.objects.filter(vigente=True, materia__carrera__in=usuario.carrera.all())
        .select_related('materia')
    )
    materia_ids = [m.materia_id for m in mesas]

    inscripciones_propias = {
        um.materia_id: um
        for um in usuarios_materia.objects.filter(usuario_id=usuario.id, materia_id__in=materia_ids)
    }
    materias_con_mesa_inscripta = set(
        InscripcionFinal.objects.filter(
            usuario_id=usuario.id, llamado__materia_id__in=materia_ids
        ).values_list('llamado__materia_id', flat=True)
    )

    correlativas_por_materia = {}
    for c in MateriaCorrelativa.objects.filter(materia_id__in=materia_ids).select_related('materia_correlativa'):
        correlativas_por_materia.setdefault(c.materia_id, []).append(c)

    correlativa_ids = {c.materia_correlativa_id for lista in correlativas_por_materia.values() for c in lista}
    inscripciones_correlativas = _inscripciones_por_materia(usuario.id, correlativa_ids) if correlativa_ids else {}

    resultado = []
    for mesa in mesas:
        if mesa.materia_id in materias_con_mesa_inscripta:
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': "Ya estás inscripto en una mesa de esta materia"})
            continue

        inscripcion_materia = inscripciones_propias.get(mesa.materia_id)
        if inscripcion_materia is None:
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': "No estás inscripto en esta materia"})
            continue

        if inscripcion_materia.modalidad != 'Libre' and (
            inscripcion_materia.nota_cursada is None or inscripcion_materia.nota_cursada < 7
        ):
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': "Necesitás nota de cursada ≥ 7 (o modalidad libre)"})
            continue

        if tiene_final_aprobado(inscripcion_materia):
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': f"Ya aprobaste el final de {mesa.materia}"})
            continue

        correlativas = correlativas_por_materia.get(mesa.materia_id, [])
        faltantes = [
            c.materia_correlativa for c in correlativas
            if not tiene_final_aprobado(inscripciones_correlativas.get(c.materia_correlativa_id))
        ]
        if faltantes:
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': _motivo_finales_faltantes(faltantes)})
            continue

        # Llegar acá significa que cumple TODOS los requisitos académicos; lo
        # único que puede faltar es la ventana de inscripción, que es
        # justamente el caso que habilita la inscripción excepcional.
        if not mesa.inscripcion_vigente():
            resultado.append({'mesa': mesa, 'disponible': False, 'motivo': MOTIVO_INSCRIPCION_CERRADA})
        else:
            resultado.append({'mesa': mesa, 'disponible': True, 'motivo': None})

    return resultado
