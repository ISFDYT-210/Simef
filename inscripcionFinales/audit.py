"""Utilidad para registrar acciones de auditoría en SIMEF.

Los registros no se modifican ni se borran (#271): ver RegistroAuditoria. Hasta
que la institución defina cuánto tiempo se conservan las actas y notas, no se
borra ninguno. Antes se borraban solos los de más de un año.
"""
from .models import RegistroAuditoria


def _texto(valor):
    return '' if valor is None else str(valor)


def registrar_auditoria(request, accion, modelo='', objeto_id='',
                        valor_anterior=None, valor_nuevo=None, motivo=''):
    """Guarda quién hizo qué y, si corresponde, qué valor había y cuál quedó.

    El autor se copia al registro (DNI, nombre y rol), así no se pierde si
    después se da de baja la cuenta.

    Ejemplos dentro de una vista:
        registrar_auditoria(request, 'Creó el usuario con DNI 30111222', 'Usuario', nuevo.id)
        registrar_auditoria(request, 'Corrigió la nota de final', 'InscripcionFinal', insc.pk,
                            valor_anterior='nota 3', valor_nuevo='nota 6', motivo='Error de tipeo')
    """
    usuario = request.user if request.user.is_authenticated else None
    return RegistroAuditoria.objects.create(
        usuario=usuario,
        autor_dni=_texto(usuario.dni) if usuario else '',
        autor_nombre=(usuario.nombre_completo or usuario.email or '') if usuario else '',
        autor_rol=(usuario.rol or '') if usuario else '',
        accion=accion[:255],
        modelo_afectado=modelo,
        objeto_id=str(objeto_id) if objeto_id else '',
        valor_anterior=_texto(valor_anterior),
        valor_nuevo=_texto(valor_nuevo),
        motivo=motivo or '',
    )

