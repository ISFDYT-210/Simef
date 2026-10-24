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
from django.db.models import Q

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

# Sprint 3: tope de intentos para rendir el final de una materia. Ausente
# cuenta como intento consumido igual que una nota < 4; una inscripción
# todavía sin resultado cargado no consume nada. Si el alumno recursa la
# cursada, los intentos de antes del ciclo actual dejan de contar (ver
# usuarios_materia.ciclo_actual_desde).
MAX_OPORTUNIDADES_FINAL = 4


def intentos_consumidos(usuario_id, materia_id, inscripcion_materia=None):
    """Cuántas de las MAX_OPORTUNIDADES_FINAL ya se gastaron."""
    if inscripcion_materia is None:
        inscripcion_materia = usuarios_materia.objects.filter(
            usuario_id=usuario_id, materia_id=materia_id).first()
    qs = InscripcionFinal.objects.filter(usuario_id=usuario_id, llamado__materia_id=materia_id)
    if inscripcion_materia and inscripcion_materia.ciclo_actual_desde:
        qs = qs.filter(llamado__llamado__gte=inscripcion_materia.ciclo_actual_desde)
    return qs.filter(Q(ausente=True) | Q(nota__lt=4)).count()

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


def horario_ocupado(usuario_id, materia):
    """
    True si el alumno ya está cursando (EN_CURSO, es decir asistiendo a
    clases ahora mismo) otra materia que cae en el mismo día y horario que
    `materia`. Una vez que esa otra cursada queda REGULAR/PROMOCIONADO/
    APROBADO ya no ocupa el horario: el alumno dejó de asistir a esas clases.

    `materia`: instancia de Materia (ya consultada por el caller, evita
    repetir el SELECT).
    """
    conflicto = usuarios_materia.objects.filter(
        usuario_id=usuario_id,
        estado=EstadoCursada.EN_CURSO,
        materia__dia=materia.dia,
        materia__Horario=materia.Horario,
    ).exclude(materia_id=materia.id).select_related('materia').first()
    if conflicto:
        return True, f"Cursando los {materia.dia} a las {materia.Horario}"
    return False, None


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

    ocupado, motivo_horario = horario_ocupado(usuario_id, materia)
    if ocupado:
        return False, motivo_horario

    correlativas = list(
        MateriaCorrelativa.objects.filter(materia_id=materia_id).select_related('materia_correlativa')
    )
    if not correlativas:
        if materia.anio != 1 and es_ingresante(usuario_id, materia.carrera_id):
            # Sin correlativa cargada para guiarse: por las dudas, no se
            # adelantan materias de años superiores mientras siga en el
            # bloque de primer año.
            return False, "Tenés que completar primer año antes de cursar materias de años superiores"
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
    if intentos_consumidos(usuario_id, materia_id, inscripcion_materia) >= MAX_OPORTUNIDADES_FINAL:
        return False, f"Agotaste las {MAX_OPORTUNIDADES_FINAL} oportunidades para rendir el final de {materia}"

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
    todavía no cursó, cada una con si puede inscribirse y el motivo puntual
    si no puede. Pensado para el desglose de requisitos en la UI de
    lista_materias_user, en vez de ocultar sin explicar.

    Las que está cursando ahora mismo (EN_CURSO) también aparecen, marcadas
    con 'cursando': True, para que la tabla las muestre con su propio estado
    en vez de que el alumno las "pierda de vista". Las que ya cursó por
    completo (REGULAR/APROBADO/PROMOCIONADO) no son candidatas a nada de
    esto y quedan afuera.

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

    carreras_candidatas = {m.carrera_id for m in materias}
    ingresante_por_carrera = {
        carrera_id: es_ingresante(usuario.id, carrera_id) for carrera_id in carreras_candidatas
    }

    # (día, horario) -> materia que el alumno está cursando ahora mismo
    # (EN_CURSO), para el chequeo de superposición horaria.
    horario_ocupado_por = {
        (um.materia.dia, um.materia.Horario): um.materia
        for um in usuarios_materia.objects.filter(
            usuario_id=usuario.id, estado=EstadoCursada.EN_CURSO
        ).select_related('materia')
    }

    resultado = []
    for materia in materias:
        if materia.id in materias_con_inscripcion_activa:
            inscripcion = inscripciones_usuario.get(materia.id)
            if inscripcion and inscripcion.estado == EstadoCursada.EN_CURSO:
                resultado.append({
                    'materia': materia, 'disponible': False, 'motivo': 'Cursando',
                    'correlativas_faltantes': [], 'cursando': True,
                    'horario': f"{materia.dia} · {materia.Horario} hs" if materia.dia else f"{materia.Horario} hs",
                })
            continue  # ya cursada completa (REGULAR/APROBADO/PROMOCIONADO): no es candidata a nada de esto

        if materia.anio == 1 and ingresante_por_carrera.get(materia.carrera_id):
            resultado.append({
                'materia': materia, 'disponible': True, 'motivo': None,
                'correlativas_faltantes': [], 'cursando': False,
            })
            continue

        correlativas = correlativas_por_materia.get(materia.id, [])

        if not correlativas and materia.anio != 1 and ingresante_por_carrera.get(materia.carrera_id):
            # Sin correlativa cargada para guiarse: por las dudas, no se
            # adelantan materias de años superiores mientras siga en el
            # bloque de primer año.
            resultado.append({
                'materia': materia, 'disponible': False,
                'motivo': "Tenés que completar primer año antes de cursar materias de años superiores",
                'correlativas_faltantes': [], 'cursando': False,
            })
            continue

        faltantes = [
            c.materia_correlativa for c in correlativas
            if not tiene_cursada_aprobada(inscripciones_usuario.get(c.materia_correlativa_id))
        ]
        if faltantes:
            resultado.append({
                'materia': materia, 'disponible': False, 'motivo': _motivo_correlativas_faltantes(faltantes),
                'correlativas_faltantes': faltantes, 'cursando': False,
            })
            continue

        conflicto = horario_ocupado_por.get((materia.dia, materia.Horario))
        if conflicto and conflicto.id != materia.id:
            resultado.append({
                'materia': materia, 'disponible': False,
                'motivo': f"Cursando los {materia.dia} a las {materia.Horario}",
                'correlativas_faltantes': [], 'cursando': False,
            })
        else:
            resultado.append({
                'materia': materia, 'disponible': True, 'motivo': None,
                'correlativas_faltantes': [], 'cursando': False,
            })

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
    # Bloquea una segunda inscripción simultánea mientras haya una SIN
    # resultado todavía. Una vez cargado el resultado (nota o ausente), ya no
    # cuenta acá: si quedan oportunidades, el alumno puede volver a anotarse.
    materias_con_mesa_inscripta = set(
        InscripcionFinal.objects.filter(
            usuario_id=usuario.id, llamado__materia_id__in=materia_ids, aprobada__isnull=True,
        ).values_list('llamado__materia_id', flat=True)
    )

    # Intentos ya gastados por materia, para el tope de MAX_OPORTUNIDADES_FINAL
    # (una sola query para todas las mesas de esta página, no una por mesa).
    intentos_por_materia = {}
    for fila in InscripcionFinal.objects.filter(
        usuario_id=usuario.id, llamado__materia_id__in=materia_ids,
    ).values('llamado__materia_id', 'ausente', 'nota', 'llamado__llamado'):
        intentos_por_materia.setdefault(fila['llamado__materia_id'], []).append(fila)

    def _intentos_consumidos(materia_id, inscripcion_materia):
        desde = inscripcion_materia.ciclo_actual_desde if inscripcion_materia else None
        consumidos = 0
        for fila in intentos_por_materia.get(materia_id, []):
            if desde and fila['llamado__llamado'] < desde:
                continue
            if fila['ausente'] or (fila['nota'] is not None and fila['nota'] < 4):
                consumidos += 1
        return consumidos

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
            resultado.append({
                'mesa': mesa, 'disponible': False, 'motivo': None,
                'aprobada': True, 'nota': inscripcion_materia.nota_final,
            })
            continue

        if _intentos_consumidos(mesa.materia_id, inscripcion_materia) >= MAX_OPORTUNIDADES_FINAL:
            resultado.append({
                'mesa': mesa, 'disponible': False,
                'motivo': f"Agotaste las {MAX_OPORTUNIDADES_FINAL} oportunidades para rendir el final",
            })
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
