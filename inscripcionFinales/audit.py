"""Utilidad para registrar acciones de auditoría en SIMEF."""
from .models import RegistroAuditoria


def registrar_auditoria(request, accion, modelo='', objeto_id=''):
    """Guarda quién hizo qué.

    Ejemplo de uso dentro de una vista:
        registrar_auditoria(request, 'Creó el usuario juan@mail.com', 'Usuario', nuevo.id)
    """
    RegistroAuditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        accion=accion,
        modelo_afectado=modelo,
        objeto_id=str(objeto_id) if objeto_id else '',
    )
