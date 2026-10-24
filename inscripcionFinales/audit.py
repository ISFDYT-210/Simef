"""Utilidad para registrar acciones de auditoría en SIMEF."""
from datetime import timedelta
from django.utils import timezone
from .models import RegistroAuditoria

# Los registros de auditoría se conservan solo un año.
RETENCION_AUDITORIA = timedelta(days=365)


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
    RegistroAuditoria.objects.filter(
        fecha__lt=timezone.now() - RETENCION_AUDITORIA
    ).delete()
