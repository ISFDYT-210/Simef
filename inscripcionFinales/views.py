import re
import unicodedata
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from .models import *
from .forms import *
from . import correlativas
from django.views.generic import CreateView,TemplateView,ListView,UpdateView,DeleteView,FormView
from django.core.mail import send_mail
from django.contrib.auth import *
from django.contrib import messages
from django.db.models import Q,Prefetch,OuterRef,F
from django import forms
from datetime import datetime   
from django.http import HttpResponse,JsonResponse
import csv
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.core.paginator import *
from django.db import IntegrityError,models
from django.utils import timezone
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.views.decorators.csrf import csrf_protect
from math import *
from json import *
from django.template import loader
from django.template.loader import render_to_string
from django.http import HttpResponse
from io import BytesIO

from django.utils import timezone
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages
from django.shortcuts import render, redirect

# Agregar estos imports específicos para el primer login
from django.contrib.auth.forms import SetPasswordForm  # ← Nuevo
from django.contrib.auth import login    

#from weasyprint import HTML, CSS
from django.utils.timezone import now
from django.template.loader import render_to_string
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from io import BytesIO
from .models import Usuario, usuarios_materia, Materia, Carrera

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
import io
from django.utils.timezone import now
from .permissions import capacidad_requerida, rol_requerido, CapacidadRequeridaMixin
from .audit import registrar_auditoria

# ... aquí van tus otros imports existentes

class HomePageView(TemplateView):
    template_name = 'index.html'
    model=Usuario

    def get(self, request):
        return  render(request, 'index.html')
    

class CustomLoginView(LoginView):
  pass

       
class CustomLogoutView(LogoutView):

    def get(self,request):
        logout(request)
        messages.success(request, 'Su sesión se ha cerrado correctamente. Hasta la próxima!')
        return redirect("/")



class registerView(CapacidadRequeridaMixin, CreateView):
    capacidades_requeridas = ('gestionar_usuarios',)
    model = Usuario
    form_class = registri_user_form
    
    def form_valid(self, form):
        usuario_email = form.cleaned_data.get('email')
        password_generado = form.password_generado

        form.instance.first_login = True
        form.save()  # guarda el usuario, asigna carrera y (si puede) manda el mail

        messages.success(
            self.request,
            f'Usuario {usuario_email} creado correctamente. Contraseña: {password_generado}'
        )
        registrar_auditoria(self.request, f'Creó el usuario {usuario_email}', 'Usuario', form.instance.pk)
        return redirect('/user_list')
    

   
       
class editUser(UpdateView):
    model = Usuario
    form_class = profile_students_form
    template_name = 'registration/edit_profile.html'
    success_url = '/user_list/'  # Cambiar a lista de usuarios
    
    def dispatch(self, request, *args, **kwargs):
        es_perfil_propio = str(request.user.pk) == str(kwargs.get('pk'))
        if not es_perfil_propio and not request.user.tiene_capacidad('gestionar_usuarios'):
            return render(request, '403_forbidden.html', status=403)
        return super().dispatch(request, *args, **kwargs)

    def puede_editar_rol(self):
        return self.request.user.is_superuser or self.request.user.es_directivo() or self.request.user.es_secretario()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['puede_editar_rol'] = self.puede_editar_rol()
        return kwargs

    def form_valid(self, form):
        # Validaciones adicionales antes de guardar
        dni = form.cleaned_data.get('dni')
        telefono_1 = form.cleaned_data.get('telefono_1')
        telefono_2 = form.cleaned_data.get('telefono_2')

        # Validar DNI único (excluyendo el usuario actual)
        if dni and Usuario.objects.filter(dni=dni).exclude(id=self.object.id).exists():
            messages.error(self.request, 'Ya existe un usuario con ese DNI.')
            return self.form_invalid(form)

        # Validar teléfonos si están presentes
        if telefono_1 and not re.fullmatch(r'\d{10}', telefono_1):
            messages.error(self.request, 'El teléfono debe tener exactamente 10 dígitos.')
            return self.form_invalid(form)

        if telefono_2 and not re.fullmatch(r'\d{10}', telefono_2):
            messages.error(self.request, 'El celular debe tener exactamente 10 dígitos.')
            return self.form_invalid(form)

        # El campo 'rol' es dinámico y no forma parte de Meta.fields, así que
        # ModelForm no lo aplica solo: lo asignamos a mano si el usuario tiene permiso.
        if self.puede_editar_rol() and 'rol' in form.cleaned_data:
            form.instance.rol = form.cleaned_data['rol']

        # Si todo está bien, guardar y mostrar mensaje de éxito
        response = super().form_valid(form)
        messages.success(self.request, 'El usuario se ha editado correctamente.')
        return response
    
    def form_invalid(self, form):
        # Si hay errores en el formulario
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{form.fields[field].label}: {error}')
        return super().form_invalid(form)
    


@capacidad_requerida('gestionar_mesas')
def editMesa(request, pk):
    mesa = get_object_or_404(MesaFinal, pk=pk)
    
    if request.method == 'POST':
        form = MesaFinalForm(request.POST, instance=mesa)
        
        if form.is_valid():
            # Obtener la fecha del formulario validado (ya procesada por Django)
            fecha_llamado = form.cleaned_data['llamado']
            
            # Obtener fecha actual
            fecha_actual = timezone.now()
            
            if fecha_llamado > fecha_actual:
                # Guardar el formulario directamente (Django ya manejó la conversión de fecha)
                form.save()
                messages.success(request, 'Mesa final actualizada correctamente.')
                return redirect('/mesas_lista/')
            else:
                messages.error(request, 'La fecha de llamado debe ser posterior a la fecha de hoy.')
                # Agregar error al formulario para mostrarlo en el template
                form.add_error('llamado', 'La fecha de llamado debe ser posterior a la fecha de hoy.')
                return render(request, 'registration/edit_mesa.html', {'form': form})
        else:
            # Si el formulario no es válido, mostrar errores
            messages.error(request, 'Datos del formulario inválidos.')
            return render(request, 'registration/edit_mesa.html', {'form': form})
    else:
        form = MesaFinalForm(instance=mesa)
    
    return render(request, 'registration/edit_mesa.html', {'form': form})

class editInscr(UpdateView):
    model = InscripcionFinal
    form_class = InscripcionFinalForm
    template_name = 'registration/edit_inscr.html'
    success_url = '/'

class cargarNotaFinal(UpdateView):
    model = InscripcionFinal
    form_class = InscripcionFinalForm
    template_name = 'finales/cargar_nota.html'
    success_url = '/'   
     
class profileviews(TemplateView):
    model = Usuario 
  

class deleteUser(CapacidadRequeridaMixin, DeleteView):
    capacidades_requeridas = ('gestionar_usuarios',)
    model = Usuario
    template_name ='registration/delete_user.html'
    success_url = '/user_list'
    
class deleteInscripcion(CapacidadRequeridaMixin, DeleteView):
    capacidades_requeridas = ('gestionar_mesas',)
    model = InscripcionFinal
    template_name ='registration/delete_inscripcion.html'
    success_url = '/inscripcion_finales_lista'

class deleteMesa(CapacidadRequeridaMixin, DeleteView):
    capacidades_requeridas = ('gestionar_mesas',)
    model = MesaFinal
    template_name ='registration/delete_mesa.html'
    success_url = '/mesas_lista'
         

class institutoView(CreateView):
    model = Instituto
    form_class = institutoForms

    def form_valid(self, form):
        form.save()
        Instituto = form.cleaned_data.get('nombre_instituto')
        email = form.cleaned_data.get('email_instituto')
      
        
        return redirect('/')
    

class carreraView(CreateView):
       
    model = Carrera
    form_class = carreraForm

    def form_valid(self, form):
        form.save()
        Carrera = form.cleaned_data.get('nombre_carrera')
        Resolucion = form.cleaned_data.get('num_resolucion')


        return redirect('/')

@capacidad_requerida('gestionar_materias')
def lista_carreras(request):
    carreras = Carrera.objects.all().order_by('nombre_carrera')
    return render(request, 'carreras/lista_carreras.html', {'carreras': carreras})

@capacidad_requerida('gestionar_materias')
def editar_carrera(request, id):
    carrera = get_object_or_404(Carrera, id=id)
    if request.method == 'POST':
        form = carreraForm(request.POST, instance=carrera)
        if form.is_valid():
            form.save()
            return redirect('lista_carreras')
    else:
        form = carreraForm(instance=carrera)
    return render(request, 'carreras/editar_carrera.html', {'form': form, 'carrera': carrera})

class listUser(CapacidadRequeridaMixin, TemplateView):
    """Solo sirve el HTML; las filas las pide el navegador a api_lista_usuarios."""
    capacidades_requeridas = ('gestionar_usuarios',)
    template_name = 'registration/list_user.html'


def api_lista_usuarios(request):
    if not request.user.puede_gestionar_usuarios():
        return JsonResponse({'error': 'No autorizado'}, status=403)

    qs = Usuario.objects.all().order_by('rol', 'nombre_completo')

    busqueda = _sin_acentos(request.GET.get('q', ''))
    if busqueda:
        # nombre_completo ignora tildes, igual que el resto de los buscadores
        # del sistema; dni/email se buscan tal cual (ya son case-insensitive
        # por icontains). La tabla de usuarios es chica, por eso resolver el
        # nombre acá en Python no es un problema (mismo criterio que
        # api_lista_mesas con las materias).
        ids_por_nombre = [
            uid for uid, nombre in qs.values_list('id', 'nombre_completo')
            if busqueda in _sin_acentos(nombre)
        ]
        qs = qs.filter(
            Q(id__in=ids_por_nombre) | Q(dni__icontains=busqueda) | Q(email__icontains=busqueda)
        )

    return _pagina_json(qs, request, lambda u: {
        'id': u.id,
        'email': u.email,
        'nombre_completo': u.nombre_completo,
        'dni': u.dni,
        'rol': u.rol,
        'rol_display': u.get_rol_display(),
    })


ROLES_AUDITABLES = ('Directivo', 'Secretario', 'Preceptor', 'Profesor')


class listAuditoria(CapacidadRequeridaMixin, ListView):
    capacidades_requeridas = ('ver_auditoria',)
    model = RegistroAuditoria
    template_name = 'registration/list_auditoria.html'
    paginate_by = 25

    def get_queryset(self):
        queryset = RegistroAuditoria.objects.select_related('usuario').filter(
            usuario__rol__in=ROLES_AUDITABLES
        )

        rol_filter = self.request.GET.get('rol')
        if rol_filter in ROLES_AUDITABLES:
            queryset = queryset.filter(usuario__rol=rol_filter)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(usuario__nombre_completo__icontains=search) |
                Q(usuario__email__icontains=search) |
                Q(accion__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = [(r, dict(Usuario.ROL_CHOICES)[r]) for r in ROLES_AUDITABLES]
        context['rol_actual'] = self.request.GET.get('rol', '')
        context['search_actual'] = self.request.GET.get('search', '')
        return context


def _sin_acentos(texto):
    """'Matemática' -> 'matematica'. Para que buscar sin tildes igual encuentre."""
    sin_tildes = unicodedata.normalize('NFD', str(texto or ''))
    sin_tildes = ''.join(c for c in sin_tildes if unicodedata.category(c) != 'Mn')
    return sin_tildes.lower().strip()


def _pagina_json(queryset, request, armar_fila, por_pagina=10):
    """Pagina en la base (LIMIT/OFFSET) y devuelve el JSON que consumen los listados."""
    paginator = Paginator(queryset, por_pagina)
    page = paginator.get_page(request.GET.get('page', 1))
    return JsonResponse({
        'results': [armar_fila(obj) for obj in page.object_list],
        'page': page.number,
        'num_pages': paginator.num_pages,
        'count': paginator.count,
    })


class listInscripcion(TemplateView):
    """Solo sirve el HTML; las filas las pide el navegador a api_lista_inscripciones."""
    template_name = 'registration/list_inscripcion.html'


def api_lista_inscripciones(request):
    if not request.user.puede_administrar():
        return JsonResponse({'error': 'No autorizado'}, status=403)

    qs = InscripcionFinal.objects.select_related('usuario', 'llamado__materia').order_by('usuario__nombre_completo')

    return _pagina_json(qs, request, lambda insc: {
        'id': insc.id,
        'usuario': str(insc.usuario),
        'llamado': str(insc.llamado),
    })


class listMesa(TemplateView):
    """Solo sirve el HTML; las filas las pide el navegador a api_lista_mesas."""
    template_name = 'registration/mesas_finales_lista.html'


def api_lista_mesas(request):
    es_profesor = request.user.es_profesor() and not request.user.puede_gestionar_mesas()
    if not (request.user.puede_gestionar_mesas() or es_profesor):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    qs = MesaFinal.objects.select_related('materia').order_by('-llamado')
    if es_profesor:
        # El profesor solo ve las mesas de las materias que dicta
        qs = qs.filter(materia__profesor=request.user)

    busqueda = _sin_acentos(request.GET.get('q', ''))
    if busqueda:
        # La búsqueda del listado ignora tildes. Como 'translate' no existe en
        # SQLite, resolvemos las materias que coinciden acá (la tabla es chica)
        # y filtramos por id, que funciona igual en Postgres y en SQLite.
        ids = [
            mid for mid, nombre in Materia.objects.values_list('id', 'nombre_materia')
            if busqueda in _sin_acentos(nombre)
        ]
        qs = qs.filter(materia_id__in=ids)

    return _pagina_json(qs, request, lambda mesa: {
        'id': mesa.id,
        'materia': str(mesa.materia),
        'fecha': mesa.llamado.strftime('%d/%m/%Y'),
        'hora': mesa.llamado.strftime('%H:%M'),
        # inscripcion_vigente distingue "abierta de verdad" de "quedó abierta pero venció"
        'vigente': mesa.inscripcion_vigente(),
        'abierta': mesa.inscripcionAbierta,
    })
   
   
class showUser(ListView):
    model = Usuario
    template_name = 'registration/show_user.html'


def lista_materias_user(request):
    materias_con_requisitos = correlativas.materias_con_requisitos(request.user)
    return render(request, 'materias/lista_materias_disponibles_user.html', {'materias_con_requisitos': materias_con_requisitos})

def lista_materias_inscriptas_user(request):
    usuario = request.user.id
    materias_inscriptas = usuarios_materia.objects.filter(
        usuario_id=usuario,
        aprobada=False
    ).select_related('materia')
    
    return render(request, 'materias/lista_materias_inscriptas_user.html', {'materias': materias_inscriptas})

def lista_materias_inscriptas_adm(request):
    if not (request.user.puede_administrar() or request.user.puede_cargar_notas()):
        return render(request, '403_forbidden.html', status=403)
    materias_inscriptas = usuarios_materia.objects.select_related('materia', 'usuario').order_by('usuario__nombre_completo')
    if request.user.es_profesor() and not request.user.is_superuser:
        # El profesor solo ve a sus propios alumnos, no los de toda la escuela
        materias_inscriptas = materias_inscriptas.filter(materia__profesor=request.user)
    return render(request, 'materias/lista_materias_inscriptas_adm.html', {'materias': materias_inscriptas})

@capacidad_requerida('ver_materias')
def lista_materias_admin(request):
    carreras = Carrera.objects.all()
    materias_all = Materia.objects.all().order_by('anio')  
    query_carrera = request.GET.get('carrera')
    query_anio = request.GET.get('anio')
    filters = Q()
    
    if query_carrera:
        filters &= Q(carrera__id=query_carrera)

    if query_anio:
        filters &= Q(anio=query_anio)

    if filters:
        materias_all = materias_all.filter(filters)

    paginator = Paginator(materias_all, 10)
    page = request.GET.get('page')
    try:
        materias = paginator.page(page)
    except PageNotAnInteger:
        materias = paginator.page(1)
    except EmptyPage:
        materias = paginator.page(paginator.num_pages)
    
    return render(request, 'materias/lista_materias_admin.html', {'materias': materias, 'carreras': carreras})    

@capacidad_requerida('gestionar_materias')
def alta_materia(request):
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
           form.save()
           return redirect('exito_alta_materia')
          
    else:
        form = MateriaForm()
        print(form)
    return render(request, 'materias/alta_materia.html', {'form': form})


def exito_cambios_materia(request):
    return render(request, 'materias/exito_cambios_materia.html')

def exito_alta_materia(request):
    return render(request, 'materias/exito_alta_materia.html')
def alerta_materia_existente(request):
    return render(request, 'alerta_materia_existente')

def listarMateriasFinal(request):
    materias_final = []
    materias_disponibles=usuarios_materia.objects.filter(usuario=request.user,aprobada=False)
    for m in materias_disponibles:
        if m.puede_inscribirse_en_mesa_final() and MesaFinal.objects.filter(materia=m.materia,vigente=True).exists():
            for mf in MesaFinal.objects.filter(materia=m.materia,vigente=True):
                materias_final.append(mf)
    return render(request, 'listarMateriasFinal.html', {'materias_final' : materias_final})

@capacidad_requerida('gestionar_mesas')
def altaMesa(request):
    if request.method == 'POST':
        form = MesaFinalForm(request.POST)
        fecha_llamado_str = request.POST.get('llamado')
        
        try:
            # Parsear como datetime naive
            fecha_llamado_naive = datetime.strptime(fecha_llamado_str, '%Y-%m-%dT%H:%M')
            
            # Convertir a timezone-aware usando la zona horaria del proyecto
            fecha_llamado = timezone.make_aware(fecha_llamado_naive)
            
            # Obtener fecha actual (ya es timezone-aware)
            fecha_actual = timezone.now()
            
            print(fecha_llamado)
            print(fecha_actual)
            
            if form.is_valid():
                if fecha_llamado > fecha_actual:
                    form.save()
                    return redirect('list_mesa')
                else:
                    return JsonResponse({'status': 'error', 'message': 'La fecha de llamado debe ser posterior a la fecha de hoy'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Datos del formulario inválidos'})
                
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Formato de fecha inválido'})
    else:
        form = MesaFinalForm()

    context = {
        'form': form,
        'carreras': Carrera.objects.all().order_by('nombre_carrera'),
        'anios': Materia.ANIO_CHOICES,
    }
    return render(request, 'finales/alta_mesa_final.html', context)

def lista_finales_user(request):
    finales_con_requisitos = correlativas.finales_con_requisitos(request.user)
    return render(request, 'finales/lista_finales_disponibles_user.html', {'finales_con_requisitos': finales_con_requisitos})

def lista_finales_inscriptos_user(request):
    usuario = request.user.id
    finales_inscriptos = InscripcionFinal.objects.filter(
        usuario_id=usuario,
        aprobada=None
    )
    return render(request, 'finales/lista_finales_inscriptos_user.html', {'finales': finales_inscriptos})

def _finales_inscriptos_visibles(usuario):
    """Inscripciones a final pendientes que este usuario tiene permitido ver."""
    qs = InscripcionFinal.objects.filter(
        Q(aprobada=False) | Q(aprobada__isnull=True)
    ).select_related('llamado__materia', 'usuario')
    if usuario.es_profesor() and not usuario.is_superuser:
        # El profesor solo ve a sus propios alumnos, no los de toda la escuela
        qs = qs.filter(llamado__materia__profesor=usuario)
    return qs


def lista_finales_inscriptos_adm(request):
    """Solo sirve el HTML; las filas las pide el navegador a api_finales_inscriptos_adm."""
    if not (request.user.puede_administrar() or request.user.puede_cargar_notas()):
        return render(request, '403_forbidden.html', status=403)
    return render(request, 'finales/lista_finales_inscriptos_adm.html')


def api_finales_inscriptos_adm(request):
    if not (request.user.puede_administrar() or request.user.puede_cargar_notas()):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    qs = _finales_inscriptos_visibles(request.user).order_by('usuario__nombre_completo')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        qs = qs.filter(
            Q(llamado__materia__nombre_materia__icontains=busqueda) |
            Q(usuario__nombre_completo__icontains=busqueda)
        )

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page', 1))
    finales = list(page.object_list)

    # Una sola query para las notas de toda la página, en vez de una por fila
    pares = {(f.usuario_id, f.llamado.materia_id) for f in finales}
    notas_por_par = defaultdict(list)
    if pares:
        for nota in usuarios_materia.objects.filter(
            usuario_id__in={p[0] for p in pares},
            materia_id__in={p[1] for p in pares},
        ):
            notas_por_par[(nota.usuario_id, nota.materia_id)].append(nota.nota_final)

    return JsonResponse({
        'results': [{
            'id': f.id,
            'mesa_id': f.llamado_id,
            'materia': str(f.llamado.materia),
            'anio': f.llamado.materia.anio,
            'fecha': f.llamado.llamado.strftime('%d/%m/%Y'),
            'hora': f.llamado.llamado.strftime('%H:%M'),
            'estudiante': f.usuario.nombre_completo,
            'dni': f.usuario.dni,
            'notas': notas_por_par.get((f.usuario_id, f.llamado.materia_id), []),
        } for f in finales],
        'page': page.number,
        'num_pages': paginator.num_pages,
        'count': paginator.count,
    })

@capacidad_requerida('gestionar_mesas')
def inscripcionMesa(request):
    if request.method == 'POST':
        form = InscripcionFinalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('finales/inscripcion_final.html')  # Redirige a la página de éxito de inscripción
    else:
        form = InscripcionFinalForm()
    return render(request, 'finales/inscripcion_final.html', {'form': form})

def exito_inscripcion_final(request):
    return render(request, 'finales/exito_inscripcion_final.html')

################################################################
@capacidad_requerida('gestionar_mesas')
def inscripcionFinal(request):
    """Inscripción manual de un estudiante a una mesa de final (Preceptor/Directivo/Secretario)."""
    anios_por_estudiante = defaultdict(set)
    for anio, usuario_id in usuarios_materia.objects.values_list('materia__anio', 'usuario_id'):
        anios_por_estudiante[usuario_id].add(str(anio))

    estudiantes = list(
        Usuario.objects.filter(rol='Estudiante').prefetch_related('carrera').order_by('nombre_completo')
    )
    for estudiante in estudiantes:
        estudiante.anios_csv = ','.join(sorted(anios_por_estudiante.get(estudiante.id, [])))
        estudiante.carreras_csv = ','.join(str(c.id) for c in estudiante.carrera.all())

    context = {
        'estudiantes': estudiantes,
        'carreras': Carrera.objects.all().order_by('nombre_carrera'),
        'anios': Materia.ANIO_CHOICES,
    }
    return render(request, 'finales/inscripcion_final_adm.html', context)


def inscripcionFinalEst(request, final_id):
    final = get_object_or_404(MesaFinal, id=final_id)
    
    if request.method == 'GET':
        inscripcion_usuario = request.user
        
        # Verificar si ya existe la inscripción
        if InscripcionFinal.objects.filter(usuario=inscripcion_usuario, llamado=final).exists():
            messages.warning(request, 'Ya estás inscrito en este final.')
            return redirect('/inscripcionFinalEst/')

        # Verificar que la mesa esté dentro de su período de inscripción
        if not final.inscripcion_vigente():
            messages.error(request, 'La inscripción para esta mesa de final está cerrada.')
            return redirect('/inscripcionFinalEst/')

        # Validar la inscripción
        if validar_inscripcion_final(inscripcion_usuario.id, final.materia):
            # Crear el objeto InscripcionFinal
            nueva_inscripcion = InscripcionFinal(
                usuario=inscripcion_usuario,
                llamado=final,
            )
            nueva_inscripcion.save()
            
            messages.success(request, 'Te has inscrito exitosamente en el final.')
            return redirect('/inscripcionFinalEst/')
        else:
            messages.error(request, 'No cumples con los requisitos para inscribirte en este final.')
            return redirect('/inscripcionFinalEst/')
    
    # Si es GET, mostrar el formulario de confirmación
    return render(request, 'finals/inscripcion_final_adm.html', {'final': final})

@capacidad_requerida('abrir_inscripciones')
def obtener_materias_estudiante(request):
    """Vista AJAX: materias con inscripción abierta que pertenecen a la carrera del estudiante"""
    estudiante_id = request.GET.get('estudiante_id')
    if not estudiante_id:
        return JsonResponse({'status': 'error', 'message': 'ID de estudiante requerido'})

    estudiante = get_object_or_404(Usuario, id=estudiante_id)
    materias = Materia.objects.filter(
        inscripcionAbierta=True,
        carrera__in=estudiante.carrera.all()
    ).order_by('nombre_materia')

    return JsonResponse({
        'status': 'success',
        'materias': [{'id': m.id, 'nombre': m.nombre_materia} for m in materias]
    })

@capacidad_requerida('abrir_inscripciones')
def inscripcionMateria(request):
    if request.method == 'POST':
        inscripcion_usuario=request.POST['usuario']
        inscripcion_materia=request.POST['materia']
        form = InscripcionMateriaForm(request.POST)
        if form.is_valid():
            if usuarios_materia.objects.filter(usuario=inscripcion_usuario, materia=inscripcion_materia).count()<1:
                form.save()
                return redirect('exito_inscripcion_mesa')  # Redirige a pagina de exito de alta de mesa
            else:
                return redirect('error_inscripcion_adm')             
    else:
        form = InscripcionMateriaForm()
    return render(request, 'materias/inscripcion_materia_adm.html',  {'form': form}) 

def inscripcionMateriaEst(request, materia_id,modalidad):
    materia = get_object_or_404(Materia, id=materia_id)
    
    if request.method == 'GET':
        inscripcion_usuario = request.user
        
        # Si ya tiene una cursada activa de esta materia no puede reinscribirse;
        # si lo que tiene es RECURSA/ABANDONO, sí puede (recursar).
        if correlativas.tiene_inscripcion_activa(inscripcion_usuario.id, materia_id):
            messages.warning(request, 'Ya estás inscrito en esta materia.')
            return redirect('/inscripcionMateriaEst')
        
        # Validar la inscripción
        if validar_inscripcion_materias(inscripcion_usuario.id, materia_id):
            # Crear el objeto usuarios_materia
            nueva_inscripcion = usuarios_materia(
                usuario=inscripcion_usuario,
                materia=materia,
                modalidad=modalidad
            )
            nueva_inscripcion.save()
            
            messages.success(request, 'Te has inscrito exitosamente en la materia.')
            return redirect('/inscripcionMateriaEst')
        else:
            messages.error(request, 'No cumples con los requisitos para inscribirte en esta materia.')
            return redirect('/inscripcionMateriaEst')
    
    # Si es GET, mostrar el formulario de confirmación
    return render(request, 'materias/inscripcion_materia_est.html', {'materia': materia})

def exito_inscripcion_mesa(request):
    return render(request, 'finales/exito_inscripcion_mesa.html')

def error_alta_mesa(request):
    return render(request, 'finales/error_alta_mesa.html')

def exito_alta_mesa(request):
    return render(request, 'finales/exito_alta_mesa.html')

def error_inscripcion_adm(request):
    return render(request, 'finales/error_inscripcion_adm.html')

def error_inscripcion_est(request):#No tenes la nota de cursada minima
    return render(request, 'finales/error_inscripcion_est.html')
def error_inscripcion_est1(request):#No tenes la nota de cursada minima
    return render(request, 'finales/error_inscripcion_est1.html')
def error_inscripcion_est2(request):#Ya tenes nota de final no te podes volver a inscribir
    return render(request, 'finales/error_inscripcion_est2.html')
def error_inscripcion_est3(request):#No estas inscripto a la materia
    return render(request, 'finales/error_inscripcion_est3.html')
def error_inscripcion_est5(request):#No aprobaste la correlativa
    return render(request, 'finales/error_inscripcion_est5.html')
def error_inscripcion_est6(request):#No cursaste la correlativa
    return render(request, 'finales/error_inscripcion_est6.html')
    
################################################################

#Nico y Cami were here

def crear_estudiante(request):
    if request.method == 'POST':
        form = EstudianteForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = EstudianteForm()
    return render(request, 'crear_estudiante.html', {'form':form})

def crear_profesor(request):
    if request.method =='POST':
        form = ProfesorForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = ProfesorForm()
        return render(request, 'crear_profesor.html', {'form':form})
    

def crear_preceptor(request):
    if request.method =='POST':
        form = PreceptorForm(request.Post)
        if form.is_valid():
            form.save()
    else:
        form = PreceptorForm()
        return render(request, 'crear_preceptor.html',{'form':form})
    

def crear_Directivo(request):
    if request.method =='POST':
        form = DirectivoForm(request.Post)
        if form.is_valid():
            form.save()
    else:
        form = DirectivoForm()
        return render(request, 'crear_directivo.html',{'form':form})
    
    
class EstudianteCreateView(CreateView):
    model = Estudiante
    fields = ['username', 'password', 'matricula', ]
    template_name = 'estudiante_form.html'
    success_url = reverse_lazy('estudiante_lista')

class EstudianteUpdateView(UpdateView):
    model = Estudiante
    fields = ['username', 'matricula',]
    template_name = 'estudiante.form.html'
    success_url = reverse_lazy('estudiante_lista')

class EstudianteDeleteView(DeleteView):
    model = Estudiante
    template_name = 'confirmar_eliminar_estudiante.html'
    success_url = reverse_lazy('estudiante_lista')
    


def _cargar_nota_de_fila(usuario, fila, carrera_obj, numero_fila, errores):
    """
    Si la fila del CSV de carga masiva de usuarios trae columna 'Materia',
    busca (o crea) la inscripción de ese usuario a esa materia y le carga
    Modalidad / Nota de cursada / Nota de final si vienen. Así una misma
    carga sirve para dar de alta al usuario y para cargarle la nota, sin
    necesidad de un archivo aparte. Devuelve True si cargó algo.
    """
    nombre_materia = (fila.get('Materia') or '').strip()
    if not nombre_materia:
        return False

    materias_candidatas = Materia.objects.filter(nombre_materia__iexact=nombre_materia)
    if carrera_obj:
        materias_candidatas = materias_candidatas.filter(carrera=carrera_obj)
    materia = materias_candidatas.first()
    if not materia:
        errores.append(f'Fila {numero_fila}: Materia no encontrada ({nombre_materia})')
        return False

    inscripcion, _creada = usuarios_materia.objects.get_or_create(usuario=usuario, materia=materia)

    modalidad = (fila.get('Modalidad') or '').strip()
    if modalidad:
        modalidades_validas = {codigo for codigo, _etiqueta in MODALIDAD_CHOICES}
        if modalidad not in modalidades_validas:
            errores.append(
                f'Fila {numero_fila}: Modalidad inválida ({modalidad}). Opciones: {", ".join(modalidades_validas)}'
            )
        else:
            inscripcion.modalidad = modalidad

    cargo_algo = False
    for columna, campo in (('Nota de cursada', 'nota_cursada'), ('Nota de final', 'nota_final')):
        valor = (fila.get(columna) or '').strip()
        if not valor:
            continue
        try:
            nota = float(valor.replace(',', '.'))
            if not (0 <= nota <= 10):
                raise ValueError
        except ValueError:
            errores.append(f'Fila {numero_fila}: {columna} inválida ({valor})')
            continue
        setattr(inscripcion, campo, nota)
        if campo == 'nota_final':
            inscripcion.aprobada = nota >= 4
        cargo_algo = True

    inscripcion.save()
    return cargo_algo


@capacidad_requerida('gestionar_usuarios')
def cargar_usuarios(request):
    if request.method == 'POST':
        formulario = ArchivoForm(request.POST, request.FILES)
        
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Por favor seleccione un archivo CSV.')
            formulario = ArchivoForm()
            return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})
        
        if formulario.is_valid():
            archivo_csv = request.FILES['csv_file']
            
            try:
                # Intentar diferentes encodings
                contenido = None
                for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                    try:
                        archivo_csv.seek(0)
                        contenido = archivo_csv.read().decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if contenido is None:
                    messages.error(request, 'No se pudo leer el archivo. Verifique la codificación.')
                    return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})
                
                # Procesar CSV
                lineas = contenido.splitlines()
                reader = csv.DictReader(lineas, delimiter=',')
                
                usuarios_creados = 0
                usuarios_duplicados = 0
                notas_cargadas = 0
                errores = []
                
                # Validar encabezados requeridos
                campos_requeridos = ['Correo electrónico', 'Nombre estudiante', 'Documento estudiante']
                if not all(campo in reader.fieldnames for campo in campos_requeridos):
                    messages.error(request, f'El archivo debe contener las columnas: {", ".join(campos_requeridos)}')
                    return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})
                
                for numero_fila, fila in enumerate(reader, start=2):
                    try:
                        # Campos obligatorios
                        email = fila.get('Correo electrónico', '').strip()
                        nombre_completo = fila.get('Nombre estudiante', '').strip()
                        dni_str = fila.get('Documento estudiante', '').strip()
                        
                        # Validaciones básicas
                        if not email or not nombre_completo or not dni_str:
                            errores.append(f'Fila {numero_fila}: Campos obligatorios faltantes (email, nombre o DNI)')
                            continue
                        
                        # Validar email
                        from django.core.validators import validate_email
                        try:
                            validate_email(email)
                        except:
                            errores.append(f'Fila {numero_fila}: Email inválido ({email})')
                            continue
                        
                        # Validar y convertir DNI
                        try:
                            dni = int(dni_str)
                            if dni <= 0:
                                raise ValueError()
                        except ValueError:
                            errores.append(f'Fila {numero_fila}: DNI inválido ({dni_str})')
                            continue
                        
                        # Si el usuario ya existe no se recrea, pero igual se le
                        # carga la materia/nota (y se le suma la carrera) si la
                        # fila las trae: así no hace falta un CSV aparte para
                        # cargar notas de alumnos que ya están en el sistema.
                        usuario_existente = Usuario.objects.filter(Q(email=email) | Q(dni=dni)).first()
                        if usuario_existente:
                            usuarios_duplicados += 1
                            carrera_para_notas = None
                            if fila.get('Carrera', '').strip():
                                carrera_para_notas = Carrera.objects.filter(
                                    nombre_carrera__iexact=fila['Carrera'].strip()
                                ).first()
                                if carrera_para_notas and not usuario_existente.carrera.filter(id=carrera_para_notas.id).exists():
                                    usuario_existente.carrera.add(carrera_para_notas)
                            if _cargar_nota_de_fila(usuario_existente, fila, carrera_para_notas, numero_fila, errores):
                                notas_cargadas += 1
                            continue

                        # Campos opcionales con validaciones
                        username = fila.get('Username', '').strip() or str(dni)
                        
                        # Fecha de nacimiento
                        fecha_nac = None
                        if fila.get('Fecha nacimiento', '').strip():
                            try:
                                from datetime import datetime
                                fecha_str = fila['Fecha nacimiento'].strip()
                                formatos = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
                                for formato in formatos:
                                    try:
                                        fecha_nac = datetime.strptime(fecha_str, formato).date()
                                        break
                                    except ValueError:
                                        continue
                            except:
                                errores.append(f'Fila {numero_fila}: Fecha inválida ({fecha_str})')
                                continue
                        
                        # Teléfonos
                        telefono_1 = None
                        telefono_2 = None
                        
                        if fila.get('Telefono 1', '').strip():
                            telefono_1 = fila['Telefono 1'].strip()
                            if not re.fullmatch(r'\d{10}', telefono_1):
                                errores.append(f'Fila {numero_fila}: Teléfono 1 debe tener exactamente 10 dígitos')
                                continue

                        if fila.get('Telefono 2', '').strip():
                            telefono_2 = fila['Telefono 2'].strip()
                            if not re.fullmatch(r'\d{10}', telefono_2):
                                errores.append(f'Fila {numero_fila}: Teléfono 2 debe tener exactamente 10 dígitos')
                                continue
                        
                        # Estado civil (validar que sea una opción válida)
                        estado_civil = fila.get('Estado civil', '').strip()
                        estados_validos = ['Soltero', 'Soltera', 'Casado', 'Casada', 'Divorciado', 'Divorciada', 'Viudo', 'Viuda']
                        if estado_civil and estado_civil not in estados_validos:
                            errores.append(f'Fila {numero_fila}: Estado civil inválido. Opciones: {", ".join(estados_validos)}')
                            continue
                        
                        # Sexo
                        sexo = fila.get('Sexo', '').strip().upper()
                        if sexo and sexo not in ['M', 'F', 'MASCULINO', 'FEMENINO']:
                            errores.append(f'Fila {numero_fila}: Sexo inválido. Usar: M, F, Masculino o Femenino')
                            continue
                        
                        # Normalizar sexo
                        if sexo in ['MASCULINO']:
                            sexo = 'M'
                        elif sexo in ['FEMENINO']:
                            sexo = 'F'
                        
                        # Rol (por defecto Estudiante)
                        rol = fila.get('Rol', '').strip() or 'Estudiante'
                        roles_validos = ['Estudiante', 'Profesor', 'Directivo', 'Preceptor', 'Administrador', 'Bibliotecario']
                        if rol not in roles_validos:
                            errores.append(f'Fila {numero_fila}: Rol inválido. Opciones: {", ".join(roles_validos)}')
                            continue
                        
                        # Buscar carrera si se especifica
                        carrera_obj = None
                        if fila.get('Carrera', '').strip():
                            try:
                                carrera_obj = Carrera.objects.get(nombre_carrera__iexact=fila['Carrera'].strip())
                            except Carrera.DoesNotExist:
                                errores.append(f'Fila {numero_fila}: Carrera no encontrada ({fila["Carrera"].strip()})')
                                continue
                        
                        # Crear usuario según el rol
                        password = PASSWORD_PREDETERMINADA  # Contraseña inicial antes del primer login
                        
                        if rol == 'Estudiante':
                            matricula = fila.get('Matricula', str(dni))  # Usar DNI como matrícula por defecto
                            
                            usuario = Estudiante.objects.create_user(
                                email=email,
                                nombre_completo=nombre_completo,
                                dni=dni,
                                username=username,
                                password=password,
                                matricula=matricula,
                                fecha_nac=fecha_nac,
                                telefono_1=telefono_1,
                                telefono_2=telefono_2,
                                direccion=fila.get('Direccion', '').strip() or None,
                                localidad=fila.get('Localidad', '').strip() or None,
                                ciudad=fila.get('Ciudad', '').strip() or None,
                                nacionalidad=fila.get('Nacionalidad', 'Argentina').strip(),
                                estado_civil=estado_civil or None,
                                sexo=sexo or None,
                                rol=rol
                            )
                            
                        elif rol == 'Profesor':
                            especialidad = fila.get('Especialidad', '').strip() or 'No especificada'
                            
                            usuario = Profesor.objects.create_user(
                                email=email,
                                nombre_completo=nombre_completo,
                                dni=dni,
                                username=username,
                                password=password,
                                fecha_nac=fecha_nac,
                                telefono_1=telefono_1,
                                telefono_2=telefono_2,
                                direccion=fila.get('Direccion', '').strip() or None,
                                localidad=fila.get('Localidad', '').strip() or None,
                                ciudad=fila.get('Ciudad', '').strip() or None,
                                nacionalidad=fila.get('Nacionalidad', 'Argentina').strip(),
                                estado_civil=estado_civil or None,
                                sexo=sexo or None,
                                rol=rol,
                                especialidad=especialidad
                            )
                            
                        elif rol == 'Directivo':
                            cargo = fila.get('Cargo', '').strip() or 'No especificado'
                            
                            usuario = Directivo.objects.create_user(
                                email=email,
                                nombre_completo=nombre_completo,
                                dni=dni,
                                username=username,
                                password=password,
                                fecha_nac=fecha_nac,
                                telefono_1=telefono_1,
                                telefono_2=telefono_2,
                                direccion=fila.get('Direccion', '').strip() or None,
                                localidad=fila.get('Localidad', '').strip() or None,
                                ciudad=fila.get('Ciudad', '').strip() or None,
                                nacionalidad=fila.get('Nacionalidad', 'Argentina').strip(),
                                estado_civil=estado_civil or None,
                                sexo=sexo or None,
                                rol=rol,
                                cargo=cargo
                            )
                            
                        elif rol == 'Preceptor':
                            area = fila.get('Area', '').strip() or 'No especificada'
                            
                            usuario = Preceptor.objects.create_user(
                                email=email,
                                nombre_completo=nombre_completo,
                                dni=dni,
                                username=username,
                                password=password,
                                fecha_nac=fecha_nac,
                                telefono_1=telefono_1,
                                telefono_2=telefono_2,
                                direccion=fila.get('Direccion', '').strip() or None,
                                localidad=fila.get('Localidad', '').strip() or None,
                                ciudad=fila.get('Ciudad', '').strip() or None,
                                nacionalidad=fila.get('Nacionalidad', 'Argentina').strip(),
                                estado_civil=estado_civil or None,
                                sexo=sexo or None,
                                rol=rol,
                                area=area
                            )
                            
                        else:  # Usuario base para Administrador, Bibliotecario, etc.
                            usuario = Usuario.objects.create_user(
                                email=email,
                                nombre_completo=nombre_completo,
                                dni=dni,
                                username=username,
                                password=password,
                                fecha_nac=fecha_nac,
                                telefono_1=telefono_1,
                                telefono_2=telefono_2,
                                direccion=fila.get('Direccion', '').strip() or None,
                                localidad=fila.get('Localidad', '').strip() or None,
                                ciudad=fila.get('Ciudad', '').strip() or None,
                                nacionalidad=fila.get('Nacionalidad', 'Argentina').strip(),
                                estado_civil=estado_civil or None,
                                sexo=sexo or None,
                                rol=rol
                            )
                        
                        # Asignar carrera si se encontró
                        if carrera_obj:
                            usuario.carrera.add(carrera_obj)

                        if _cargar_nota_de_fila(usuario, fila, carrera_obj, numero_fila, errores):
                            notas_cargadas += 1

                        usuarios_creados += 1
                        
                    except IntegrityError as e:
                        if 'UNIQUE constraint' in str(e):
                            usuarios_duplicados += 1
                        else:
                            errores.append(f'Fila {numero_fila}: Error de integridad - {str(e)}')
                    except Exception as e:
                        errores.append(f'Fila {numero_fila}: Error inesperado - {str(e)}')
                
                # Mostrar resultados
                if errores:
                    partes = [f'{usuarios_creados} usuario(s) creado(s)']
                    if notas_cargadas:
                        partes.append(f'{notas_cargadas} nota(s) cargada(s)')
                    messages.warning(request, ', '.join(partes) + ', con algunas advertencias.')
                    return render(request, 'registration/warning_carga_masiva.html', {
                        'usuarios_creados': usuarios_creados,
                        'usuarios_duplicados': usuarios_duplicados,
                        'notas_cargadas': notas_cargadas,
                        'errores': errores[:20]  # Mostrar máximo 20 errores
                    })
                elif usuarios_creados > 0 or notas_cargadas > 0:
                    partes = []
                    if usuarios_creados:
                        partes.append(f'{usuarios_creados} usuario(s) creado(s)')
                    if notas_cargadas:
                        partes.append(f'{notas_cargadas} nota(s) cargada(s)')
                    messages.success(request, ', '.join(partes) + ' correctamente.')
                    return render(request, 'registration/exito_carga_masiva.html', {
                        'usuarios_creados': usuarios_creados,
                        'usuarios_duplicados': usuarios_duplicados,
                        'notas_cargadas': notas_cargadas,
                    })
                elif usuarios_duplicados > 0:
                    messages.warning(request, f'{usuarios_duplicados} usuario(s) ya existían en el sistema; no había notas para cargarles.')
                    return render(request, 'registration/warning_carga_masiva.html', {
                        'usuarios_creados': 0,
                        'usuarios_duplicados': usuarios_duplicados,
                        'notas_cargadas': 0,
                        'errores': []
                    })
                else:
                    messages.error(request, 'No se pudo procesar ninguna fila del archivo.')
                    return render(request, 'registration/cargar_usuarios.html', {
                        'formulario': formulario,
                        'errores': errores[:20]
                    })
                    
            except Exception as e:
                messages.error(request, f'Error procesando archivo: {str(e)}')
                return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})
        else:
            # Formulario no válido
            return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})
    
    else:
        formulario = ArchivoForm()
    
    return render(request, 'registration/cargar_usuarios.html', {'formulario': formulario})

@capacidad_requerida('gestionar_materias')
def alta_masiva_materia(request):
    if request.method == 'POST':
        form = ArchivoForm(request.POST, request.FILES)

        if 'csv_file' not in request.FILES:
            messages.error(request, 'Por favor seleccione un archivo CSV.')
            return render(request, 'materias/alta_masiva_materia.html', {'form': ArchivoForm()})

        if not form.is_valid():
            return render(request, 'materias/alta_masiva_materia.html', {'form': form})

        archivo_csv = request.FILES['csv_file']

        try:
            contenido = None
            for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                try:
                    archivo_csv.seek(0)
                    contenido = archivo_csv.read().decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if contenido is None:
                messages.error(request, 'No se pudo leer el archivo. Verifique la codificación.')
                return render(request, 'materias/alta_masiva_materia.html', {'form': form})

            reader = csv.DictReader(contenido.splitlines(), delimiter=',')

            campos_requeridos = ['Nombre materia', 'Carrera']
            if not reader.fieldnames or not all(campo in reader.fieldnames for campo in campos_requeridos):
                messages.error(request, f'El archivo debe contener las columnas: {", ".join(campos_requeridos)}')
                return render(request, 'materias/alta_masiva_materia.html', {'form': form})

            anios_validos = [str(v) for v, _ in Materia.ANIO_CHOICES]
            dias_validos = [v for v, _ in Materia.DIA_CHOICES]
            horarios_validos = [v for v, _ in Materia.HORARIO_CHOICES]

            materias_creadas = 0
            materias_duplicadas = 0
            errores = []

            for numero_fila, fila in enumerate(reader, start=2):
                try:
                    nombre_materia = fila.get('Nombre materia', '').strip()
                    nombre_carrera = fila.get('Carrera', '').strip()

                    if not nombre_materia or not nombre_carrera:
                        errores.append(f'Fila {numero_fila}: Campos obligatorios faltantes (Nombre materia, Carrera)')
                        continue

                    try:
                        carrera_obj = Carrera.objects.get(nombre_carrera__iexact=nombre_carrera)
                    except Carrera.DoesNotExist:
                        errores.append(f'Fila {numero_fila}: Carrera no encontrada ({nombre_carrera})')
                        continue

                    if Materia.objects.filter(nombre_materia__iexact=nombre_materia, carrera=carrera_obj).exists():
                        materias_duplicadas += 1
                        continue

                    profesor_obj = None
                    dni_profesor = fila.get('Profesor DNI', '').strip()
                    if dni_profesor:
                        try:
                            profesor_obj = Usuario.objects.get(dni=int(dni_profesor), rol='Profesor')
                        except (ValueError, Usuario.DoesNotExist):
                            errores.append(f'Fila {numero_fila}: Profesor no encontrado (DNI {dni_profesor})')
                            continue

                    anio = fila.get('Año', '').strip() or '1'
                    if anio not in anios_validos:
                        errores.append(f'Fila {numero_fila}: Año inválido. Opciones: {", ".join(anios_validos)}')
                        continue

                    dia = fila.get('Día', '').strip() or 'Lunes'
                    if dia not in dias_validos:
                        errores.append(f'Fila {numero_fila}: Día inválido. Opciones: {", ".join(dias_validos)}')
                        continue

                    horario = fila.get('Horario', '').strip() or '12:00'
                    if horario not in horarios_validos:
                        errores.append(f'Fila {numero_fila}: Horario inválido. Opciones: {", ".join(horarios_validos)}')
                        continue

                    inscripcion_str = fila.get('Inscripcion abierta', '').strip().lower()
                    inscripcion_abierta = inscripcion_str in ['si', 'sí', 'true', '1']

                    Materia.objects.create(
                        nombre_materia=nombre_materia,
                        carrera=carrera_obj,
                        profesor=profesor_obj,
                        anio=int(anio),
                        dia=dia,
                        Horario=horario,
                        inscripcionAbierta=inscripcion_abierta,
                    )
                    materias_creadas += 1

                except IntegrityError as e:
                    errores.append(f'Fila {numero_fila}: Error de integridad - {str(e)}')
                except Exception as e:
                    errores.append(f'Fila {numero_fila}: Error inesperado - {str(e)}')

            if materias_creadas > 0 and not errores:
                messages.success(request, f'Se crearon {materias_creadas} materias exitosamente')
                return render(request, 'materias/exito_carga_masiva.html', {
                    'materias_creadas': materias_creadas,
                    'materias_duplicadas': materias_duplicadas,
                })
            elif materias_creadas > 0:
                messages.warning(request, f'Se crearon {materias_creadas} materias con algunas advertencias')
                return render(request, 'materias/warning_carga_masiva.html', {
                    'materias_creadas': materias_creadas,
                    'materias_duplicadas': materias_duplicadas,
                    'errores': errores[:20],
                })
            elif materias_duplicadas > 0 and not errores:
                messages.warning(request, f'{materias_duplicadas} materias ya existían en el sistema')
                return render(request, 'materias/warning_carga_masiva.html', {
                    'materias_creadas': 0,
                    'materias_duplicadas': materias_duplicadas,
                    'errores': [],
                })
            else:
                messages.error(request, 'No se pudieron crear materias')
                return render(request, 'materias/alta_masiva_materia.html', {
                    'form': form,
                    'errores': errores[:20],
                })

        except Exception as e:
            messages.error(request, f'Error procesando archivo: {str(e)}')
            return render(request, 'materias/alta_masiva_materia.html', {'form': form})

    else:
        form = ArchivoForm()

    return render(request, 'materias/alta_masiva_materia.html', {'form': form})
    return render(request, 'alta_masiva_materia.html') 
    
@capacidad_requerida('gestionar_materias')
def editar_materia(request, id):
    materia = get_object_or_404(Materia, id=id)
    if request.method == 'POST':
        form = MateriaForm(request.POST, instance=materia)
        if form.is_valid():
            form.save()
            return redirect('exito_cambios_materia')
    else:
        form = MateriaForm(instance=materia)
        return render(request, 'materias/editar_materia.html', {'form': form})


    
@capacidad_requerida('gestionar_materias')
def eliminar_materia(request, id):
    materia = get_object_or_404(Materia, pk=id)
    if request.method == 'POST':
        materia.delete()
        return redirect('exito_materia_eliminada_adm')
    return render(request, 'materias/eliminar_materia.html', {'materia': materia})

def eliminar_mesa(request, id):
    mesa = get_object_or_404(MesaFinal, pk=id)
    if request.method == 'POST':
        mesa.delete()
        return redirect('exito_mesa_eliminada')
    return render(request, 'mesas/eliminar_mesa.html', {'mesa': mesa})

def eliminar_inscripcion_final(request, id):
    """Solo el personal que gestiona mesas puede dar de baja una inscripción a
    final. El estudiante no puede: una vez inscripto en una mesa, la baja
    queda a criterio de la institución."""
    final = get_object_or_404(InscripcionFinal, pk=id)
    if not request.user.tiene_capacidad('gestionar_mesas'):
        return render(request, '403_forbidden.html', status=403)
    if request.method == 'POST':
        final.delete()
        return redirect('exito_final_eliminado_adm')
    return render(request, 'finales/eliminar_final_est.html', {'final': final})

@capacidad_requerida('gestionar_materias')
def eliminar_materias_seleccionadas(request):
    if request.method == 'POST':
        materia_ids = request.POST.getlist('materia_ids')
        cantidad_eliminadas = len(materia_ids)
        if cantidad_eliminadas > 0:
            Materia.objects.filter(id__in=materia_ids).delete()
        materias = Materia.objects.all()
        return render(request, 'materias/lista_materias_admin.html',
                      {'materias': materias, 'cantidad_eliminadas': cantidad_eliminadas})
    return redirect("lista_materias_admin")


@capacidad_requerida('abrir_inscripciones')
def abrir_materias_seleccionadas(request):
    if request.method == 'POST':
        materia_ids = request.POST.getlist('materia_ids')
        if len(materia_ids) > 0:
            Materia.objects.filter(id__in=materia_ids).update(inscripcionAbierta=True)
    return redirect(reverse_lazy('lista_materias_admin'))


@capacidad_requerida('abrir_inscripciones')
def cerrar_materias_seleccionadas(request):
    if request.method == 'POST':
        materia_ids = request.POST.getlist('materia_ids')
        if len(materia_ids) > 0:
            Materia.objects.filter(id__in=materia_ids).update(inscripcionAbierta=False)
    return redirect(reverse_lazy('lista_materias_admin'))


@capacidad_requerida('gestionar_mesas')
def eliminar_mesas_seleccionadas(request):
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesa_ids')
        if len(mesa_ids) > 0:
            MesaFinal.objects.filter(id__in=mesa_ids).delete()
    return redirect('/mesas_lista')


@capacidad_requerida('gestionar_mesas')
def abrir_mesas_seleccionadas(request):
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesa_ids')
        if len(mesa_ids) > 0:
            MesaFinal.objects.filter(id__in=mesa_ids).update(inscripcionAbierta=True)
    return redirect('/mesas_lista')


@capacidad_requerida('gestionar_mesas')
def cerrar_mesas_seleccionadas(request):
    if request.method == 'POST':
        mesa_ids = request.POST.getlist('mesa_ids')
        if len(mesa_ids) > 0:
            MesaFinal.objects.filter(id__in=mesa_ids).update(inscripcionAbierta=False)
    return redirect('/mesas_lista')

#def eliminar_inscripcion_materia(request, id):
#    materia = get_object_or_404(usuarios_materia, pk=id)
#    if request.user.id==materia.usuario_id and not request.user.is_staff and not request.user.is_superuser:
#        if request.method == 'POST':
#            materia.delete()
#            return redirect('exito_materia_eliminada_est')
#        return render(request, 'materias/eliminar_materia_est.html', {'materia': materia})
#    elif request.user.is_staff or request.user.is_superuser:
#        if request.method == 'POST':
#            materia.delete()
#            return redirect('exito_materia_eliminada_adm')
#        return render(request, 'materias/eliminar_materia_est.html', {'materia': materia})        
#    else:
#        return render(request,'403_forbidden.html')
    
def eliminar_inscripcion_materia(request, id):
    """
    Dar de baja una inscripción a materia es una acción administrativa: el
    alumno no puede autogestionarla, solo Preceptor, Directivo, Secretario o
    superuser (ver Usuario.puede_administrar). No se borra el registro: se
    marca estado=ABANDONO para que el historial académico quede intacto.
    """
    materia = get_object_or_404(usuarios_materia, pk=id)
    if not request.user.puede_administrar():
        return render(request, '403_forbidden.html', status=403)
    if request.method == 'POST':
        InscripcionFinal.objects.filter(
            Q(usuario=materia.usuario) & Q(llamado__materia=materia.materia)
        ).delete()
        materia.estado = EstadoCursada.ABANDONO
        materia.save()
        registrar_auditoria(
            request, f'Dio de baja (abandono) a {materia.usuario.nombre_completo} de {materia.materia}',
            'usuarios_materia', materia.pk
        )
        return redirect('exito_materia_eliminada_adm')
    return render(request, 'materias/eliminar_materia_est.html', {'materia': materia})

def exito_materia_eliminada(request):
    return render(request, 'materias/exito_materia_eliminada.html')

def exito_materia_eliminada_adm(request):
    return render(request, 'materias/exito_materia_eliminada_adm.html')

def exito_materia_eliminada_est(request):
    return render(request, 'materias/exito_materia_eliminada_est.html')

def exito_final_eliminado_est(request):
    return render(request, 'finales/exito_final_eliminado_est.html')

def exito_final_eliminado_adm(request):
    return render(request, 'finales/exito_final_eliminado_adm.html')

@capacidad_requerida('ver_materias')
def ver_materias(request, id):
    materia = get_object_or_404(Materia, pk=id)
    return render(request, 'materias/ver_materia.html', {'materia': materia})

def cambiar_contraseña (request):
    if request.method == 'POST':
        
        username = User.objects.get(username='username')
        
        contraseña_nueva = request.POST['contraseña_nueva']
        
        username.set_password(contraseña_nueva)
        
        username.save()
        
        return HttpResponse('Su contraseña se cambio con exito')
    else : 
        return render(request, 'registration/change_password.html')  
    
  
def alta_estudiante(request):
        if request.method == 'POST' :
            form = EstudianteForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect (request, 'alta_exitosa.html')
        else:
            form = EstudianteForm()
            return render(request, 'alta_estudiante.html', {'form': form})
        
class MesasFinalesListView(ListView):
    model = MesaFinal
    template_name = 'finales/mesas_finales_list.html'
    context_object_name = 'mesas_finales'

def inscribir_mesa_final(request):
    if request.method == 'POST':
        filtro_form = FiltroInscripcionForm(request.POST)
        if filtro_form.is_valid():
            estudiante = filtro_form.cleaned_data.get('estudiante')
            materia = filtro_form.cleaned_data.get('materia')
            # Agrega lógica para filtrar según estudiante y/o materia
            mesas_finales = MesaFinal.objects.filter(materia__nombre__icontains=materia,inscripcionfinal__usuario__nombre__icontains=estudiante)
        else:
            mesas_finales = MesaFinal.objects.all()
    else:
        filtro_form = FiltroInscripcionForm()
        mesas_finales = MesaFinal.objects.all()

    context = {'mesas_finales': mesas_finales, 'filtro_form': filtro_form}
    return render(request, 'finales/inscribir_mesa_final.html', context)

@capacidad_requerida('gestionar_mesas')
def tribunal_mesa(request, mesa_id):
    """Ver y asignar el tribunal (Presidente/Vocales) de una mesa de final."""
    mesa = get_object_or_404(MesaFinal, id=mesa_id)
    tribunal_activo = mesa.tribunal.filter(activo=True).select_related('docente')
    presidente = tribunal_activo.filter(rol=TribunalMesa.PRESIDENTE).first()
    vocales = list(tribunal_activo.filter(rol=TribunalMesa.VOCAL))

    if request.method == 'POST':
        docente = get_object_or_404(Usuario, id=request.POST.get('docente'), rol='Profesor')
        rol = request.POST.get('rol')

        if rol == TribunalMesa.PRESIDENTE and presidente:
            messages.error(request, 'Esta mesa ya tiene un presidente asignado; reemplazalo en vez de agregar otro.')
        elif rol == TribunalMesa.VOCAL and len(vocales) >= TribunalMesa.MAX_VOCALES_POR_MESA:
            messages.error(request, f'Esta mesa ya tiene {TribunalMesa.MAX_VOCALES_POR_MESA} vocales asignados; reemplazá uno en vez de agregar otro.')
        elif rol not in (TribunalMesa.PRESIDENTE, TribunalMesa.VOCAL):
            messages.error(request, 'Rol inválido.')
        else:
            TribunalMesa.objects.create(mesa=mesa, docente=docente, rol=rol)
            registrar_auditoria(
                request, f'Asignó a {docente.nombre_completo} como {rol} del tribunal de {mesa.materia} ({mesa.llamado:%d/%m/%Y})',
                'TribunalMesa', mesa.pk
            )
            messages.success(request, f'{docente.nombre_completo} fue asignado como {rol}.')
        return redirect('tribunal_mesa', mesa_id=mesa.id)

    context = {
        'mesa': mesa,
        'presidente': presidente,
        'vocales': vocales,
        'profesores': Usuario.obtener_profesores(),
        'max_vocales': TribunalMesa.MAX_VOCALES_POR_MESA,
    }
    return render(request, 'finales/tribunal_mesa.html', context)


@capacidad_requerida('gestionar_mesas')
def reemplazar_tribunal(request, tribunal_id):
    """Reemplazo urgente de un integrante del tribunal: no toca el acta, solo cambia quién figura activo."""
    actual = get_object_or_404(TribunalMesa, id=tribunal_id, activo=True)
    if request.method == 'POST':
        nuevo_docente = get_object_or_404(Usuario, id=request.POST.get('docente'), rol='Profesor')
        actual.activo = False
        actual.save()
        nuevo = TribunalMesa.objects.create(
            mesa=actual.mesa, docente=nuevo_docente, rol=actual.rol, reemplaza_a=actual
        )
        registrar_auditoria(
            request,
            f'Reemplazó a {actual.docente.nombre_completo} por {nuevo_docente.nombre_completo} como {actual.rol} '
            f'en el tribunal de {actual.mesa.materia} ({actual.mesa.llamado:%d/%m/%Y})',
            'TribunalMesa', nuevo.pk
        )
        messages.success(request, f'{actual.docente.nombre_completo} fue reemplazado por {nuevo_docente.nombre_completo}.')
    return redirect('tribunal_mesa', mesa_id=actual.mesa_id)


@capacidad_requerida('gestionar_mesas')
def quitar_tribunal(request, tribunal_id):
    """Saca a alguien del tribunal sin reemplazo (deja el puesto vacante)."""
    actual = get_object_or_404(TribunalMesa, id=tribunal_id, activo=True)
    if request.method == 'POST':
        actual.activo = False
        actual.save()
        registrar_auditoria(
            request,
            f'Quitó a {actual.docente.nombre_completo} del tribunal de {actual.mesa.materia} ({actual.mesa.llamado:%d/%m/%Y}) sin reemplazo',
            'TribunalMesa', actual.pk
        )
        messages.success(request, f'{actual.docente.nombre_completo} fue quitado del tribunal.')
    return redirect('tribunal_mesa', mesa_id=actual.mesa_id)


def acta_volante(request, final_id):
    """Genera el acta volante (planilla de examen) de una mesa de final, paginada de a 25 alumnos.

    La puede ver quien gestiona mesas (Directivo/Secretario/Preceptor) o el
    profesor de la materia de esta mesa en particular."""
    final = get_object_or_404(MesaFinal, id=final_id)
    if not request.user.is_authenticated or not request.user.puede_ver_acta_de(final):
        return render(request, '403_forbidden.html', status=403)
    pages = []
    finales_inscriptos = InscripcionFinal.objects.filter(llamado=final_id).order_by('usuario__nombre_completo')
    tribunal_activo = final.tribunal.filter(activo=True).select_related('docente')
    presidente = tribunal_activo.filter(rol=TribunalMesa.PRESIDENTE).first()
    vocales = list(tribunal_activo.filter(rol=TribunalMesa.VOCAL))
    if finales_inscriptos.count() <= 25:
        context = {
            'finales_inscriptos': finales_inscriptos,
            'final': final,
            'cant_inscriptos': finales_inscriptos.count(),
            'piso': 0,
            'presidente': presidente,
            'vocales': vocales,
        }
        return render(request, 'finales/acta_volante.html', context)
    else:
        for i in range(1, ceil(finales_inscriptos.count() / 25) + 1):
            inscriptos = []
            for inscripto in range(25 * (i - 1), 25 * (i - 1) + 25):
                try:
                    inscriptos.append(finales_inscriptos[inscripto])
                except IndexError:
                    pass
            context = {
                'finales_inscriptos': inscriptos,
                'final': final,
                'cant_inscriptos': finales_inscriptos.count(),
                'piso': 25 * (i - 1),
                'presidente': presidente,
                'vocales': vocales,
            }
            html = render(request, 'finales/acta_volante.html', context).content.decode('utf-8')
            pages.append({
                'id': f'page_{i}',
                'title': f'Acta volante {i}: {final.materia}',
                'content': html
            })
        pages_json = dumps(pages)
        return render(request, 'finales/lista_acta_volante.html', {'pages_json': pages_json})

@capacidad_requerida('ver_materias')
def listar_usuarios_materia(request):
    usuarios_materia_data = usuarios_materia.objects.all()  # Recupera todos los registros de usuarios_materia
    context = {'usuarios_materia_data': usuarios_materia_data}
    return render(request, 'registration/ver_usuarios_materia.html', context)


# NOTA: la validación de inscripción a finales vive más abajo, en
# validar_inscripcion_final(). Acá había una segunda definición con el mismo
# nombre que Python descartaba (gana la última), y que además se comportaba
# distinto: ignoraba la modalidad Libre y bloqueaba a quien tuviera cualquier
# nota de final, incluso desaprobada. Se eliminó para que no se edite por error.

def validar_inscripcion_materias(usuario_id, materia_id):
    """Para cursar: cursada aprobada de cada correlativa (ver inscripcionFinales/correlativas.py)."""
    puede, _motivo = correlativas.puede_cursar(usuario_id, materia_id)
    return puede



def inscribir_usuario(usuario, materia):
    # Verificar si ya existe una inscripción para este usuario y materia
    inscripcion, created = InscripcionFinal.objects.get_or_create(
        Usuario=usuario,
        Materia=materia,
        defaults={
            'Fecha_Inscripcion': timezone.now()
        }
    )
    
    if not created:
        # Si la inscripción ya existía, actualizamos la fecha de inscripción
        inscripcion.Fecha_Inscripcion = timezone.now()
        inscripcion.save()

@capacidad_requerida('cargar_notas')
def cargar_nota_final(request, inscripcion_id):
    inscripcion = get_object_or_404(InscripcionFinal, id=inscripcion_id)
    usuario_materia = get_object_or_404(usuarios_materia, usuario=inscripcion.usuario, materia=inscripcion.llamado.materia)

    if not request.user.puede_cargar_notas_de(inscripcion.llamado.materia):
        return render(request, '403_forbidden.html', status=403)

    if request.method == 'POST':
       form = NotaFinalForm(request.POST)
       if form.is_valid():
            nota_final = form.cleaned_data['nota_final']
            usuario_materia.nota_final = nota_final
            usuario_materia.aprobada = nota_final >= 4
            usuario_materia.save()
            inscripcion.aprobada = nota_final >= 4
            inscripcion.save()

            registrar_auditoria(
                request, f'Cargó nota final {nota_final} a {inscripcion.usuario.nombre_completo} en {inscripcion.llamado.materia}',
                'usuarios_materia', usuario_materia.pk
            )
            messages.success(request, f'Nota final cargada correctamente: {nota_final}')
            return redirect('/listaFinalesAdm')  # Ajusta esto a tu URL de redirección
    else:
        form = NotaFinalForm()

    context = {
        'form': form,
        'inscripcion': inscripcion,
        'usuario_materia': usuario_materia,
    }
    return render(request, 'finales/cargar_nota.html', context)

@capacidad_requerida('cargar_notas')
def cargar_nota_cursada(request, id):
    usuario_materia = get_object_or_404(usuarios_materia, id=id)

    if not request.user.puede_cargar_notas_de(usuario_materia.materia):
        return render(request, '403_forbidden.html', status=403)

    if request.method == 'POST':
        form = NotaCursadaForm(request.POST)
        if form.is_valid():
            nota_cursada = form.cleaned_data['nota_cursada']
            usuario_materia.nota_cursada = nota_cursada
            usuario_materia.save()

            registrar_auditoria(
                request, f'Cargó nota de cursada {nota_cursada} a {usuario_materia.usuario.nombre_completo} en {usuario_materia.materia}',
                'usuarios_materia', usuario_materia.pk
            )
            messages.success(request, f'Nota de cursada cargada correctamente: {nota_cursada}')
            return redirect('/listaMateriasAdm')  # Ajusta esto a tu URL de redirección
    else:
        form = NotaCursadaForm()

    context = {
        'form': form,
        'usuarios_materia': usuario_materia,
    }
    return render(request, 'materias/cargar_nota.html', context)

@capacidad_requerida('cargar_notas')
def editar_notas(request, id):
    usuario_materia = get_object_or_404(usuarios_materia, id=id)

    if not request.user.puede_cargar_notas_de(usuario_materia.materia):
        return render(request, '403_forbidden.html', status=403)

    if request.method == 'POST':
        form = NotaCursadaForm(request.POST, instance=usuario_materia)
        if form.is_valid():
            form.save()
            registrar_auditoria(
                request, f'Editó las notas de {usuario_materia.usuario.nombre_completo} en {usuario_materia.materia}',
                'usuarios_materia', usuario_materia.pk
            )
            messages.success(request, 'Las notas han sido actualizadas correctamente.')
            return redirect('/listaMateriasAdm/')
        else:
            # Agregar mensajes de error específicos
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':  # Errores generales del formulario
                        messages.error(request, error)
                    else:
                        field_name = form.fields[field].label or field
                        messages.error(request, f'{field_name}: {error}')
    else:
        form = NotaCursadaForm(instance=usuario_materia)
    
    context = {
        'form': form,
        'usuarios_materia': usuario_materia,  # Cambiar el nombre de la variable para que coincida con el template
    }
    return render(request, 'materias/cargar_nota.html', context)



@capacidad_requerida('abrir_inscripciones')
def abrir_inscripcion_materia(request, carrera, anio):
    Materia.objects.filter(carrera_id=carrera, anio=anio).update(inscripcionAbierta=True)
    return redirect('lista_materias_admin')


@capacidad_requerida('abrir_inscripciones')
def cerrar_inscripcion_materia(request, carrera, anio):
    Materia.objects.filter(carrera_id=carrera, anio=anio).update(inscripcionAbierta=False)
    return redirect('lista_materias_admin')
    
@capacidad_requerida('gestionar_usuarios')
def eliminar_usuarios(request):
    if request.method == 'POST':
        # Eliminar múltiples usuarios seleccionados
        usuarios_ids = request.POST.getlist('usuarios_ids')
        
        # Verificar que no se elimine a sí mismo
        if str(request.user.id) in usuarios_ids:
            messages.error(request, "No puedes eliminar tu propio usuario.")
            return redirect('list_user')
        
        # Verificar que se hayan seleccionado usuarios
        if len(usuarios_ids) > 0:
            try:
                # Eliminar los usuarios seleccionados
                emails = list(Usuario.objects.filter(id__in=usuarios_ids).values_list('email', flat=True))
                registrar_auditoria(request, f'Eliminó usuarios: {", ".join(emails)}', 'Usuario', ",".join(usuarios_ids))
                usuarios_eliminados = Usuario.objects.filter(id__in=usuarios_ids)
                cantidad_eliminadas = usuarios_eliminados.count()
                usuarios_eliminados.delete()
                
                messages.success(request, f'Se eliminaron {cantidad_eliminadas} usuarios correctamente.')
            except Exception as e:
                messages.error(request, f'Error al eliminar usuarios: {str(e)}')
        else:
            messages.warning(request, 'No se seleccionaron usuarios para eliminar.')

    return redirect('list_user')

@rol_requerido('Directivo', 'Secretario')
def blanquear_password(request, usuario_id):
    """Restablece la contraseña de un usuario a la predeterminada. Solo Directivo, Secretario o super admin."""
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if request.method == 'POST':
        usuario.set_password(PASSWORD_PREDETERMINADA)
        usuario.first_login = True
        usuario.save()
        registrar_auditoria(request, f'Blanqueó la contraseña de {usuario.email}', 'Usuario', usuario.pk)
        messages.success(request, f'Se blanqueó la contraseña de {usuario.nombre_completo or usuario.email}. Ahora es "{PASSWORD_PREDETERMINADA}" y deberá cambiarla en su próximo inicio de sesión.')
        return redirect('list_user')
    return render(request, 'registration/blanquear_password.html', {'usuario': usuario})

@capacidad_requerida('gestionar_mesas')
def inscribir_final(request):
    """Vista AJAX para realizar la inscripción al final"""
    usuario_id = request.POST.get('usuario')
    llamado_id = request.POST.get('llamado')
    excepcional = request.POST.get('excepcional') == 'true'

    if not usuario_id or not llamado_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Datos incompletos'
        })

    try:
        usuario = get_object_or_404(Usuario, id=usuario_id)
        mesa_final = get_object_or_404(MesaFinal, id=llamado_id)

        # Verificar que el usuario sea estudiante
        if usuario.rol != 'Estudiante':
            return JsonResponse({
                'status': 'error',
                'message': 'Solo los estudiantes pueden inscribirse'
            })

        # Ventana normal de inscripción, o excepcional si está pedida y todavía
        # faltan los días mínimos para el examen (ver MesaFinal.LIMITE_DIAS_EXCEPCION).
        if excepcional:
            if not mesa_final.inscripcion_excepcional_vigente():
                return JsonResponse({
                    'status': 'error',
                    'message': f'La inscripción excepcional ya no está disponible: faltan menos de {MesaFinal.LIMITE_DIAS_EXCEPCION} días para el examen'
                })
        elif not mesa_final.inscripcion_vigente():
            return JsonResponse({
                'status': 'error',
                'message': 'La inscripción para esta mesa está cerrada'
            })

        # Verificar que no esté ya inscripto
        if InscripcionFinal.objects.filter(
            usuario=usuario,
            llamado__materia=mesa_final.materia
        ).exists():
            return JsonResponse({
                'status': 'error',
                'message': f'{usuario.nombre_completo} ya está inscripto en una mesa de {mesa_final.materia.nombre_materia}'
            })
        
        # Verificar que esté inscripto en la materia
        try:
            inscripcion_materia = usuarios_materia.objects.get(
                usuario=usuario,
                materia=mesa_final.materia
            )
        except usuarios_materia.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'{usuario.nombre_completo} no está inscripto en {mesa_final.materia.nombre_materia}'
            })
        
        # Verificar nota de cursada
        if inscripcion_materia.modalidad != 'Libre':
            if inscripcion_materia.nota_cursada is None or inscripcion_materia.nota_cursada < 7:
                return JsonResponse({
                    'status': 'error',
                    'message': f'{usuario.nombre_completo} no tiene la nota mínima de cursada (7)'
                })
        
        # Verificar correlativas
        if not validar_inscripcion_final(usuario_id, mesa_final.materia.id):
            return JsonResponse({
                'status': 'error',
                'message': f'{usuario.nombre_completo} no cumple con los requisitos de correlativas'
            })
        
        # Verificar que no tenga final aprobado
        if inscripcion_materia.nota_final is not None and inscripcion_materia.nota_final >= 4:
            return JsonResponse({
                'status': 'error',
                'message': f'{usuario.nombre_completo} ya aprobó esta materia con nota {inscripcion_materia.nota_final}'
            })
        
        # Crear la inscripción
        inscripcion = InscripcionFinal.objects.create(
            usuario=usuario,
            llamado=mesa_final
        )
        prefijo = 'Inscripción EXCEPCIONAL: inscribió' if excepcional else 'Inscribió'
        registrar_auditoria(
            request, f'{prefijo} a {usuario.nombre_completo} a la mesa de {mesa_final.materia} del {mesa_final.llamado:%d/%m/%Y}',
            'InscripcionFinal', inscripcion.pk
        )

        return JsonResponse({
            'status': 'success',
            'message': f'{usuario.nombre_completo} se inscribió correctamente al final de {mesa_final.materia.nombre_materia}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error al procesar la inscripción: {str(e)}'
        })

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

def validar_inscripcion_final(usuario_id, materia_id):
    """
    Valida si un usuario puede inscribirse al final de una materia.
    Retorna True si puede inscribirse, False si no.
    """
    try:
        usuario_materia_instance = usuarios_materia.objects.get(
            usuario_id=usuario_id,
            materia_id=materia_id
        )
    except usuarios_materia.DoesNotExist:
        return False

    # Nota mínima de cursada propia de la materia para rendir (regla del
    # instituto, no es parte de correlativas): >= 7 o modalidad Libre.
    if usuario_materia_instance.modalidad != 'Libre':
        if (usuario_materia_instance.nota_cursada is None or
                usuario_materia_instance.nota_cursada < 7):
            return False

    # Correlativas: cursada aprobada de esta materia + final aprobado de cada
    # correlativa (ver inscripcionFinales/correlativas.py).
    puede, _motivo = correlativas.puede_rendir(usuario_id, materia_id)
    return puede

class FirstLoginPasswordChangeView(FormView):
    form_class = SetPasswordForm
    template_name = 'registration/first_login_password_change.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        return '/change_password_first/done/'
    
    def form_valid(self, form):
        # Cambiar la contraseña sin pedir la anterior
        form.save()
        
        # Marcar que ya no es primer login
        self.request.user.first_login = False
        self.request.user.save()
        
        # Mantener la sesión activa después del cambio
        login(self.request, self.request.user)
        
        messages.success(self.request, 'Contraseña cambiada exitosamente. Ya puedes usar el sistema normalmente.')
        return super().form_valid(form)
    
def first_login_password_change_done(request):
    return render(request, 'registration/first_login_success.html')

@capacidad_requerida('ver_reportes')
def imprimir_mesas_finales_pdf(request):
    """
    Genera un PDF con el listado de mesas de finales vigentes
    Compatible con Vercel y ambientes serverless
    """
    try:
        # Crear el PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Lista para almacenar elementos del PDF
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para subtítulo
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Título principal
        elements.append(Paragraph("MESAS DE EXÁMENES FINALES", title_style))
        
        # Fecha de generación
        fecha_actual = now().strftime('%d/%m/%Y %H:%M')
        elements.append(Paragraph(f"Generado el: {fecha_actual}", subtitle_style))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Obtener mesas finales vigentes
        mesas = MesaFinal.objects.select_related(
            'materia', 
            'materia__carrera',
            'materia__profesor'
        ).filter(vigente=True).order_by('llamado', 'materia__nombre_materia')
        
        if not mesas.exists():
            # Si no hay mesas, mostrar mensaje
            no_mesas_style = ParagraphStyle(
                'NoMesas',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.HexColor('#e74c3c'),
                alignment=TA_CENTER
            )
            elements.append(Paragraph("No hay mesas de finales vigentes en este momento", no_mesas_style))
        else:
            # Crear encabezados de la tabla
            data = [['Materia', 'Carrera', 'Fecha', 'Horario', 'Profesor', 'Inscripción']]
            
            # Agregar datos de cada mesa
            for mesa in mesas:
                # Determinar estado de inscripción
                inscripcion = "✓ Abierta" if mesa.inscripcionAbierta else "✗ Cerrada"
                
                # Obtener nombre del profesor
                profesor = mesa.materia.profesor.nombre_completo if mesa.materia.profesor and mesa.materia.profesor.nombre_completo else '-'
                
                # Obtener nombre de carrera
                carrera = mesa.materia.carrera.nombre_carrera if mesa.materia.carrera else '-'
                
                data.append([
                    mesa.materia.nombre_materia,
                    carrera,
                    mesa.llamado.strftime('%d/%m/%Y'),
                    mesa.llamado.strftime('%H:%M'),
                    profesor,
                    inscripcion
                ])
            
            # Crear tabla con anchos de columna personalizados
            table = Table(data, colWidths=[
                2.2*inch,  # Materia
                1.8*inch,  # Carrera
                0.9*inch,  # Fecha
                0.7*inch,  # Horario
                1.5*inch,  # Profesor
                0.9*inch   # Inscripción
            ])
            
            # Aplicar estilos a la tabla
            table.setStyle(TableStyle([
                # Estilo del encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Estilo del cuerpo
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#3498db')),
                
                # Alternancia de colores en filas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                
                # Padding
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
            
            # Agregar espacio y pie de página
            elements.append(Spacer(1, 0.5*inch))
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#95a5a6'),
                alignment=TA_CENTER
            )
            
            total_mesas = mesas.count()
            elements.append(Paragraph(f"Total de mesas: {total_mesas}", footer_style))
        
        # Construir el PDF
        doc.build(elements)
        
        # Obtener el contenido del PDF
        pdf = buffer.getvalue()
        buffer.close()
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="mesas_finales.pdf"'
        response.write(pdf)
        
        return response
        
    except Exception as e:
        # En caso de error, retornar mensaje descriptivo
        error_msg = f"Error al generar el PDF: {str(e)}"
        print(error_msg)  # Para logs de Vercel
        return HttpResponse(error_msg, status=500)
    
    
def render_to_pdf(template_src, context_dict={}):
    """
    Función auxiliar para convertir HTML a PDF
    """
    template = render_to_string(template_src, context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(template.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def numero_a_letras(numero):
    """
    Convierte un número decimal a su representación en letras en español
    """
    unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    decenas = ['', '', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
    especiales = ['diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve']
    
    partes = str(numero).split('.')
    parte_entera = int(partes[0])
    parte_decimal = int(partes[1]) if len(partes) > 1 else 0
    
    if parte_entera == 0:
        texto_entero = 'cero'
    elif parte_entera == 100:
        texto_entero = 'cien'
    elif parte_entera < 10:
        texto_entero = unidades[parte_entera]
    elif parte_entera < 20:
        texto_entero = especiales[parte_entera - 10]
    elif parte_entera < 30:
        if parte_entera == 20:
            texto_entero = 'veinte'
        else:
            texto_entero = 'veinti' + unidades[parte_entera - 20]
    elif parte_entera < 100:
        decena = parte_entera // 10
        unidad = parte_entera % 10
        if unidad == 0:
            texto_entero = decenas[decena]
        else:
            texto_entero = decenas[decena] + ' y ' + unidades[unidad]
    else:
        texto_entero = str(parte_entera)
    
    if parte_decimal < 10:
        texto_decimal = 'cero ' + unidades[parte_decimal] if parte_decimal > 0 else 'cero'
    elif parte_decimal < 20:
        texto_decimal = especiales[parte_decimal - 10]
    elif parte_decimal < 30:
        if parte_decimal == 20:
            texto_decimal = 'veinte'
        else:
            texto_decimal = 'veinti' + unidades[parte_decimal - 20]
    elif parte_decimal < 100:
        decena = parte_decimal // 10
        unidad = parte_decimal % 10
        if unidad == 0:
            texto_decimal = decenas[decena]
        else:
            texto_decimal = decenas[decena] + ' y ' + unidades[unidad]
    else:
        texto_decimal = str(parte_decimal)
    
    resultado = texto_entero.capitalize() + ' con ' + texto_decimal.capitalize()
    return resultado


@login_required
def reporte_estudiante_descarga(request, usuario_id):
    """
    Genera un PDF con las materias y notas del estudiante para descarga
    usando una API externa
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not request.user.is_authenticated or not request.user.puede_ver_reporte_de(usuario):
        return render(request, '403_forbidden.html', status=403)
    
    if not usuario.es_estudiante():
        return HttpResponse("Este reporte solo está disponible para estudiantes", status=403)
    
    # Obtener el contexto (mismo código que antes)
    context = obtener_contexto_reporte(usuario)
    
    # Renderizar HTML
    html_string = render_to_string('reportes/constancia_estudiante.html', context)
    
    # Usar API de conversión HTML a PDF (ejemplo con api.html2pdf.app)
    try:
        api_response = requests.post(
            'https://api.html2pdf.app/v1/generate',
            json={
                'html': html_string,
                'options': {
                    'format': 'A4',
                    'margin': {'top': '1.5cm', 'right': '1.5cm', 'bottom': '1.5cm', 'left': '1.5cm'}
                }
            },
            timeout=30
        )
        
        if api_response.status_code == 200:
            response = HttpResponse(api_response.content, content_type='application/pdf')
            nombre_archivo = f"constancia_{usuario.nombre_completo or usuario.email}.pdf".replace(" ", "_")
            response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
            return response
    except Exception as e:
        pass
    
    return HttpResponse("Error al generar el PDF", status=500)


NUMEROS_EN_LETRAS_NOTA = {
    10: "Diez", 9: "Nueve", 8: "Ocho", 7: "Siete", 6: "Seis",
    5: "Cinco", 4: "Cuatro", 3: "Tres", 2: "Dos", 1: "Uno",
}


def obtener_contexto_reporte(usuario):
    """
    Contexto de la constancia/reporte de un estudiante: sus materias reales
    (de las carreras en las que está inscripto), notas y porcentaje de
    avance. Antes esto usaba una lista de materias y un nombre de carrera
    hardcodeados (de una tecnicatura en particular), así que cualquier
    estudiante de otra carrera recibía una constancia con materias que no
    eran las suyas.
    """
    carreras = list(usuario.carrera.all())
    materias = Materia.objects.filter(carrera__in=carreras).order_by('anio', 'nombre_materia')
    inscripciones = {
        um.materia_id: um
        for um in usuarios_materia.objects.filter(usuario=usuario, materia__in=materias)
    }

    materias_por_anio = {}
    total_materias = 0
    materias_aprobadas = 0

    for materia in materias:
        total_materias += 1
        inscripcion = inscripciones.get(materia.id)

        nota_cursada = calif_cursada = nota_final = calif_final = "-"
        fecha_cursada = "-"

        if inscripcion:
            if inscripcion.nota_cursada is not None:
                nota_cursada = int(float(inscripcion.nota_cursada))
                calif_cursada = NUMEROS_EN_LETRAS_NOTA.get(nota_cursada, "-")
            if inscripcion.nota_final is not None:
                nota_final = int(float(inscripcion.nota_final))
                calif_final = NUMEROS_EN_LETRAS_NOTA.get(nota_final, "-")
            if inscripcion.ciclo_lectivo:
                fecha_cursada = str(inscripcion.ciclo_lectivo)

        if correlativas.tiene_final_aprobado(inscripcion):
            materias_aprobadas += 1

        materias_por_anio.setdefault(materia.anio, []).append({
            'nombre': materia.nombre_materia,
            'nota_cursada': nota_cursada,
            'nota_final': nota_final,
            'calif_cursada': calif_cursada,
            'calif_final': calif_final,
            'fecha': fecha_cursada,
        })

    porcentaje_aprobadas = round((materias_aprobadas / total_materias * 100), 2) if total_materias > 0 else 0
    porcentaje_en_letras = numero_a_letras(porcentaje_aprobadas)

    return {
        'usuario': usuario,
        'nombre_carrera': ' y '.join(c.nombre_carrera for c in carreras) if carreras else None,
        'resolucion_carrera': ', '.join(c.num_resolucion for c in carreras if c.num_resolucion),
        'materias_por_anio': materias_por_anio,
        'fecha_actual': now().strftime('%d/%m/%Y'),
        'total_materias': total_materias,
        'materias_aprobadas': materias_aprobadas,
        'porcentaje_aprobadas': porcentaje_aprobadas,
        'porcentaje_en_letras': porcentaje_en_letras
    }



# ========== RECUPERACIÓN DE CONTRASEÑA ==========
class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

@login_required
def reporte_estudiante_html(request, usuario_id):
    """
    Vista HTML del reporte para previsualización
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if not request.user.is_authenticated or not request.user.puede_ver_reporte_de(usuario):
        return render(request, '403_forbidden.html', status=403)
    
    if not usuario.es_estudiante():
        return HttpResponse("Este reporte solo está disponible para estudiantes", status=403)
    
    context = obtener_contexto_reporte(usuario)
    
    return render(request, 'reportes/constancia_estudiante.html', context)
@capacidad_requerida('gestionar_mesas')
def obtener_finales_estudiante(request):
    """
    Vista AJAX para la inscripción manual: finales a los que un estudiante
    puede inscribirse, más los que solo le faltan por la ventana de
    inscripción cerrada (marcados 'excepcional', ver MesaFinal.inscripcion_excepcional_vigente).
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

    estudiante_id = request.GET.get('estudiante_id')
    if not estudiante_id:
        return JsonResponse({'status': 'error', 'message': 'ID de estudiante requerido'})

    estudiante = get_object_or_404(Usuario, id=estudiante_id)
    if estudiante.rol != 'Estudiante':
        return JsonResponse({'status': 'error', 'message': 'El usuario no es un estudiante'})

    inscripciones_por_materia = {
        um.materia_id: um for um in usuarios_materia.objects.filter(usuario=estudiante)
    }

    finales_disponibles = []
    for item in correlativas.finales_con_requisitos(estudiante):
        mesa = item['mesa']
        if item['disponible']:
            excepcional = False
        elif item['motivo'] == correlativas.MOTIVO_INSCRIPCION_CERRADA and mesa.inscripcion_excepcional_vigente():
            excepcional = True
        else:
            continue

        inscripcion_materia = inscripciones_por_materia.get(mesa.materia_id)
        finales_disponibles.append({
            'id': mesa.id,
            'materia': mesa.materia.nombre_materia,
            'fecha_llamado': mesa.llamado.strftime('%d/%m/%Y %H:%M'),
            'nota_cursada': (inscripcion_materia.nota_cursada if inscripcion_materia else None) or 'Libre',
            'modalidad': (inscripcion_materia.modalidad if inscripcion_materia else None) or 'Regular',
            'excepcional': excepcional,
        })

    return JsonResponse({'status': 'success', 'finales': finales_disponibles})
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

