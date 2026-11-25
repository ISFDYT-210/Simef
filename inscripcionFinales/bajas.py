"""Bajas lógicas: dar de baja en vez de borrar (#270).

Las materias, las mesas de final, las inscripciones a final y los usuarios ya no
se borran desde el sistema: se dan de baja. Lo dado de baja deja de aparecer en
los listados y en lo que se ofrece para inscribirse, pero sus cursadas, notas,
actas e inscripciones quedan intactas, y se puede reactivar desde la pantalla
"Dados de baja".

Dos casos no se pueden dar de baja, porque esconderían un acta:
- una inscripción a final con resultado (nota, aprobado/desaprobado o ausente);
- una mesa con algún resultado cargado.
Un resultado mal cargado se corrige desde "Cargar nota", con el motivo.

Cada baja y cada reactivación queda en la auditoría (#271). Aparte, los modelos
tienen on_delete=PROTECT: ni el admin ni la consola pueden borrar algo que tenga
resultados académicos colgando.
"""
from django.db import transaction
from django.utils import timezone

from .audit import registrar_auditoria
from .models import InscripcionFinal, Materia, MesaFinal, Usuario, usuarios_materia


class BajaNoPermitida(Exception):
    """El motivo se le muestra tal cual a quien intentó la baja o la reactivación."""


def esta_de_alta(objeto):
    return objeto.is_active if isinstance(objeto, Usuario) else objeto.activo


def describir(objeto):
    """'la materia X (id 5)', para los mensajes y la auditoría."""
    if isinstance(objeto, Materia):
        return f'la materia {objeto} (id {objeto.pk})'
    if isinstance(objeto, MesaFinal):
        return f'la mesa de {objeto.materia} del {timezone.localtime(objeto.llamado):%d/%m/%Y %H:%M} (id {objeto.pk})'
    if isinstance(objeto, InscripcionFinal):
        mesa = objeto.llamado
        return (f'la inscripción de {objeto.usuario} a la mesa de {mesa.materia} '
                f'del {timezone.localtime(mesa.llamado):%d/%m/%Y} (id {objeto.pk})')
    if isinstance(objeto, Usuario):
        return f'a {objeto} (DNI {objeto.dni}, id {objeto.pk})'
    raise TypeError(f'No hay baja lógica para {type(objeto).__name__}')


def lo_que_conserva(objeto):
    """Lo que tiene asociado y queda intacto al darlo de baja, para la confirmación
    y la auditoría. Por ejemplo: ['12 cursadas', '3 mesas de final']."""
    if isinstance(objeto, Materia):
        inscripciones = InscripcionFinal.objects.filter(llamado__materia=objeto)
        cantidades = [
            (usuarios_materia.objects.filter(materia=objeto).count(), 'cursada', 'cursadas'),
            (MesaFinal.objects.filter(materia=objeto).count(), 'mesa de final', 'mesas de final'),
            (inscripciones.count(), 'inscripción a final', 'inscripciones a final'),
            (inscripciones.con_resultado().count(), 'resultado de final', 'resultados de final'),
        ]
    elif isinstance(objeto, MesaFinal):
        cantidades = [(InscripcionFinal.objects.filter(llamado=objeto, activo=True).count(),
                       'inscripción', 'inscripciones')]
    elif isinstance(objeto, Usuario):
        cantidades = [
            (usuarios_materia.objects.filter(usuario=objeto).count(), 'cursada', 'cursadas'),
            (InscripcionFinal.objects.filter(usuario=objeto).count(), 'inscripción a final', 'inscripciones a final'),
            (Materia.objects.filter(profesor=objeto).count(), 'materia a cargo', 'materias a cargo'),
        ]
    else:
        cantidades = []
    return [f'{n} {singular if n == 1 else plural}' for n, singular, plural in cantidades if n]


def _texto_conserva(objeto):
    partes = lo_que_conserva(objeto)
    return 'Conserva: ' + ', '.join(partes) + '.' if partes else 'No tenía nada asociado.'


def motivo_para_no_dar_de_baja(objeto, request=None):
    """None si se puede dar de baja; si no, el motivo para mostrar."""
    if isinstance(objeto, InscripcionFinal) and objeto.tiene_resultado():
        return ('La inscripción ya tiene el resultado cargado y es parte del acta, así que no se puede '
                'dar de baja. Si el resultado está mal, corregilo desde "Cargar nota", con el motivo.')
    if isinstance(objeto, MesaFinal):
        con_resultado = InscripcionFinal.objects.filter(llamado=objeto, activo=True).con_resultado().count()
        if con_resultado:
            return (f'La mesa ya tiene {con_resultado} resultado(s) cargado(s) en el acta, así que no se '
                    'puede dar de baja.')
    if isinstance(objeto, Usuario) and request is not None and objeto.pk == request.user.pk:
        return 'No podés darte de baja a vos mismo.'
    return None


def motivo_para_no_reactivar(objeto):
    """None si se puede reactivar; si no, el motivo para mostrar."""
    if isinstance(objeto, MesaFinal):
        if not objeto.materia.activo:
            return f'La materia {objeto.materia} está dada de baja: reactivala primero.'
        otra = MesaFinal.objects.de_alta().filter(materia=objeto.materia, llamado=objeto.llamado).exclude(pk=objeto.pk)
        if otra.exists():
            return f'Ya hay otra mesa de {objeto.materia} en ese mismo día y horario.'
    if isinstance(objeto, InscripcionFinal):
        if not objeto.llamado.activo:
            return 'La mesa está dada de baja: reactivá la mesa y sus inscripciones vuelven con ella.'
        if not objeto.usuario.is_active:
            return f'{objeto.usuario} está dado de baja: reactivá primero su cuenta.'
        pendiente = (InscripcionFinal.objects.de_alta().sin_resultado()
                     .filter(usuario=objeto.usuario, llamado__materia=objeto.llamado.materia)
                     .exclude(pk=objeto.pk))
        if pendiente.exists():
            return f'{objeto.usuario} ya está inscripto en otra mesa de {objeto.llamado.materia}.'
    return None


def _marcar(objeto, de_alta):
    if isinstance(objeto, Usuario):
        objeto.is_active = de_alta
        objeto.save(update_fields=['is_active'])
        return
    objeto.activo = de_alta
    campos = ['activo']
    if not de_alta and isinstance(objeto, (Materia, MesaFinal)):
        # Dada de baja, no puede quedar abierta a inscripciones. Al reactivarla
        # sigue cerrada: se abre a mano, como cualquier otra.
        objeto.inscripcionAbierta = False
        campos.append('inscripcionAbierta')
    objeto.save(update_fields=campos)


@transaction.atomic
def dar_de_baja(request, objeto):
    """Da de baja la materia, mesa, inscripción a final o usuario, y lo deja en
    la auditoría. Lanza BajaNoPermitida si no se puede (ver arriba)."""
    motivo = motivo_para_no_dar_de_baja(objeto, request)
    if motivo:
        raise BajaNoPermitida(motivo)
    conserva = _texto_conserva(objeto)
    _marcar(objeto, de_alta=False)
    registrar_auditoria(request, f'Dio de baja {describir(objeto)}', type(objeto).__name__, objeto.pk,
                        valor_anterior='De alta', valor_nuevo=f'De baja. {conserva}')


@transaction.atomic
def reactivar(request, objeto):
    motivo = motivo_para_no_reactivar(objeto)
    if motivo:
        raise BajaNoPermitida(motivo)
    _marcar(objeto, de_alta=True)
    registrar_auditoria(request, f'Reactivó {describir(objeto)}', type(objeto).__name__, objeto.pk,
                        valor_anterior='De baja', valor_nuevo='De alta')


def dar_de_baja_varios(request, objetos):
    """Para las acciones sobre varios seleccionados. Cada baja va por separado:
    si una no se puede, las demás siguen. Devuelve (dados_de_baja, rechazados),
    con rechazados como [(objeto, motivo), ...]."""
    dados_de_baja, rechazados = [], []
    for objeto in objetos:
        try:
            dar_de_baja(request, objeto)
        except BajaNoPermitida as error:
            rechazados.append((objeto, str(error)))
        else:
            dados_de_baja.append(objeto)
    return dados_de_baja, rechazados
