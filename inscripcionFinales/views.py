from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView    
from .models import *
from .forms import *
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



class registerView(CreateView):
    model = Usuario
    form_class = registri_user_form
    
    def form_valid(self, form):
        usuario_email = form.cleaned_data.get('email')
        password1 = form.cleaned_data.get('password1')
        
        # Crear el usuario
        nuevo_usuario = form.save(commit=False)
        nuevo_usuario.first_login = True
        nuevo_usuario.save()
        
        # DESCOMENTA Y CORRIGE ESTA LÍNEA:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject='Credenciales de acceso - Sistema Instituto',
                message=f'Bienvenido al sistema.\n\nTus credenciales de acceso son:\n- Email: {usuario_email}\n- Contraseña temporal: {password1}\n\nPor seguridad, deberás cambiar esta contraseña en tu primer ingreso.',
                from_email='proyec.i210@gmail.com',
                recipient_list=[usuario_email],
                fail_silently=False,
            )
            messages.success(self.request, f'Usuario creado exitosamente. Se han enviado las credenciales a {usuario_email}')
        except Exception as e:
            messages.warning(self.request, f'Usuario creado, pero hubo un error al enviar el email: {str(e)}')
        
        return redirect('/user_list')
    

   
       
class editUser(UpdateView):
    model = Usuario
    form_class = profile_students_form
    template_name = 'registration/edit_profile.html'
    success_url = '/user_list/'  # Cambiar a lista de usuarios
    
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
        if telefono_1 and (len(str(telefono_1)) < 6 or len(str(telefono_1)) > 15):
            messages.error(self.request, 'El teléfono debe tener entre 6 y 15 dígitos.')
            return self.form_invalid(form)
            
        if telefono_2 and (len(str(telefono_2)) < 6 or len(str(telefono_2)) > 15):
            messages.error(self.request, 'El celular debe tener entre 6 y 15 dígitos.')
            return self.form_invalid(form)
        
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
  

class deleteUser(DeleteView):
    model = Usuario
    template_name ='registration/delete_user.html'
    success_url = '/user_list'
    
class deleteInscripcion(DeleteView):
    model = InscripcionFinal
    template_name ='registration/delete_inscripcion.html'
    success_url = '/inscripcion_finales_lista'

class deleteMesa(DeleteView):
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

class listUser(ListView):
    model = Usuario
    template_name = 'registration/list_user.html'
    paginate_by = 20  # Agregar paginación
    
    def get_queryset(self):
        queryset = Usuario.objects.all().order_by('rol', 'nombre_completo')
        
        # Filtrar por rol si se especifica
        rol_filter = self.request.GET.get('rol')
        if rol_filter:
            queryset = queryset.filter(rol=rol_filter)
            
        # Filtrar por búsqueda si se especifica
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre_completo__icontains=search) |
                Q(email__icontains=search) |
                Q(dni__icontains=search)
            )
            
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar opciones de roles para filtros
        context['roles'] = Usuario.ROL_CHOICES
        context['rol_actual'] = self.request.GET.get('rol', '')
        context['search_actual'] = self.request.GET.get('search', '')
        return context
    
class listInscripcion(ListView):
    model = InscripcionFinal
    template_name = 'registration/list_inscripcion.html'

class listMesa(ListView):
    model = MesaFinal
    template_name = 'registration/mesas_finales_lista.html'
   
   
class showUser(ListView):
    model = Usuario
    template_name = 'registration/show_user.html'


def lista_materias_user(request):
    usuario = request.user.id
    materias_disponibles = []
    materias = Materia.objects.all()
    for materia in materias:
        if validar_inscripcion_materias(usuario, materia.id) and materia.inscripcionAbierta:
            materias_disponibles.append(materia)
    return render(request, 'materias/lista_materias_disponibles_user.html', {'materias': materias_disponibles})

def lista_materias_inscriptas_user(request):
    usuario = request.user.id
    materias_inscriptas = usuarios_materia.objects.filter(
        usuario_id=usuario,
        aprobada=False
    ).select_related('materia')
    
    return render(request, 'materias/lista_materias_inscriptas_user.html', {'materias': materias_inscriptas})

def lista_materias_inscriptas_adm(request):
    materias_inscriptas = usuarios_materia.objects.select_related('materia')
    return render(request, 'materias/lista_materias_inscriptas_adm.html', {'materias': materias_inscriptas})

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
        if m.puede_inscribirse_en_mesa_final() and MesaFinal.objects.filter(materia=m.materia,vigente=True).exist():
            for mf in MesaFinal.objects.filter(materia=m.materia,vigente=True):
                materias_final.append(mf)
    return render(request, 'listarMateriasFinal.html', {'materias_final' : materias_final})

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
    
    return render(request, 'finales/alta_mesa_final.html', {'form': form})

def lista_finales_user(request):
    usuario = request.user.id
    finales_disponibles = []
    finales = MesaFinal.objects.all()
    for final in finales:
        if validar_inscripcion_final(usuario, final.materia.id) and final.inscripcionAbierta and InscripcionFinal.objects.filter(usuario=usuario, llamado__materia_id=final.materia.id).count()<1:
            print(final.materia)
            print(validar_inscripcion_final(usuario, final.materia.id))
            finales_disponibles.append(final)
    return render(request, 'finales/lista_finales_disponibles_user.html', {'finales': finales_disponibles})

def lista_finales_inscriptos_user(request):
    usuario = request.user.id
    finales_inscriptos = InscripcionFinal.objects.filter(
        usuario_id=usuario,
        aprobada=None
    )
    return render(request, 'finales/lista_finales_inscriptos_user.html', {'finales': finales_inscriptos})

def lista_finales_inscriptos_adm(request):
    finales_inscriptos = InscripcionFinal.objects.filter(
        Q(aprobada=False) | Q(aprobada__isnull=True)
    ).select_related('llamado__materia', 'usuario')
    for final in finales_inscriptos:
        final.notas = usuarios_materia.objects.filter(
            usuario=final.usuario,
            materia=final.llamado.materia
    )
    return render(request, 'finales/lista_finales_inscriptos_adm.html', {'finales': finales_inscriptos})

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
def inscripcionFinal(request):
    """Vista principal para mostrar el formulario de inscripción"""
    # Verificar que solo estudiantes puedan acceder
    if request.user.rol != 'Estudiante':
        messages.error(request, 'Solo los estudiantes pueden inscribirse a mesas finales.')
        return redirect('/')
    
    # Obtener todos los estudiantes para el dropdown
    estudiantes = Usuario.objects.filter(rol='Estudiante').order_by('nombre_completo')
    
    context = {
        'estudiantes': estudiantes
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
        
        # Verificar si ya existe la inscripción
        if usuarios_materia.objects.filter(usuario=inscripcion_usuario, materia=materia).exists():
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
                        
                        # Verificar duplicados
                        if Usuario.objects.filter(Q(email=email) | Q(dni=dni)).exists():
                            usuarios_duplicados += 1
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
                            try:
                                telefono_1 = int(fila['Telefono 1'].strip())
                                if len(str(telefono_1)) < 6 or len(str(telefono_1)) > 15:
                                    errores.append(f'Fila {numero_fila}: Teléfono 1 debe tener entre 6 y 15 dígitos')
                                    continue
                            except ValueError:
                                errores.append(f'Fila {numero_fila}: Teléfono 1 inválido')
                                continue
                        
                        if fila.get('Telefono 2', '').strip():
                            try:
                                telefono_2 = int(fila['Telefono 2'].strip())
                                if len(str(telefono_2)) < 6 or len(str(telefono_2)) > 15:
                                    errores.append(f'Fila {numero_fila}: Teléfono 2 debe tener entre 6 y 15 dígitos')
                                    continue
                            except ValueError:
                                errores.append(f'Fila {numero_fila}: Teléfono 2 inválido')
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
                        password = str(dni)  # Usar DNI como contraseña inicial
                        
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
                        
                        usuarios_creados += 1
                        
                    except IntegrityError as e:
                        if 'UNIQUE constraint' in str(e):
                            usuarios_duplicados += 1
                        else:
                            errores.append(f'Fila {numero_fila}: Error de integridad - {str(e)}')
                    except Exception as e:
                        errores.append(f'Fila {numero_fila}: Error inesperado - {str(e)}')
                
                # Mostrar resultados
                if usuarios_creados > 0 and not errores:
                    messages.success(request, f'Se crearon {usuarios_creados} usuarios exitosamente')
                    return render(request, 'registration/exito_carga_masiva.html', {
                        'usuarios_creados': usuarios_creados,
                        'usuarios_duplicados': usuarios_duplicados
                    })
                elif usuarios_creados > 0:
                    messages.warning(request, f'Se crearon {usuarios_creados} usuarios con algunas advertencias')
                    return render(request, 'registration/warning_carga_masiva.html', {
                        'usuarios_creados': usuarios_creados,
                        'usuarios_duplicados': usuarios_duplicados,
                        'errores': errores[:20]  # Mostrar máximo 20 errores
                    })
                elif usuarios_duplicados > 0 and not errores:
                    messages.warning(request, f'{usuarios_duplicados} usuarios ya existían en el sistema')
                    return render(request, 'registration/warning_carga_masiva.html', {
                        'usuarios_creados': 0,
                        'usuarios_duplicados': usuarios_duplicados,
                        'errores': []
                    })
                else:
                    messages.error(request, 'No se pudieron crear usuarios')
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

def alta_masiva_materia(request):
    if request.method == 'POST' and request.Files['archivo_csv']:
        archivo_csv = request.FILES['archivo_csv']
        decoded_file = archivo_csv.read().decode('utf-8').splitlines() 
        archivo_csv= csv.DictReader(decoded_file) 

        for fila in archivo_csv:
            nombre = fila['nombre']
            profesor = fila['profesor']
            carrera = fila ['carrera']
        return HttpResponse ('Materias importadas correctamente')
    return render(request, 'alta_masiva_materia.html') 
    
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
    final = get_object_or_404(InscripcionFinal, pk=id)
    if request.user.id==final.usuario_id and not request.user.is_staff and not request.user.is_superuser:
        if request.method == 'POST':
            final.delete()
            return redirect('exito_final_eliminado_est')
        return render(request, 'finales/eliminar_final_est.html', {'final': final})
    elif request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            final.delete()
            return redirect('exito_final_eliminado_adm')
        return render(request, 'finales/eliminar_final_est.html', {'final': final})        
    else:
        return render(request,'403_forbidden.html')

def eliminar_materias_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            materia_ids = request.POST.getlist('materia_ids')
            cantidad_eliminadas = len(materia_ids)
            print(request.POST)
            if cantidad_eliminadas > 0:
                Materia.objects.filter(id__in=materia_ids).delete()
            materias = Materia.objects.all()
            return render(request, 'materias/lista_materias_admin.html', {'materias': materias, 'cantidad_eliminadas': cantidad_eliminadas})
        return redirect("lista_materias_admin")
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')
    
def abrir_materias_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            materia_ids = request.POST.getlist('materia_ids')
            cantidad_eliminadas = len(materia_ids)
            print(request.POST)
            if cantidad_eliminadas > 0:
                Materia.objects.filter(id__in=materia_ids).update(inscripcionAbierta=True)
            return redirect(reverse_lazy('lista_materias_admin'))
        else:
            return redirect(reverse_lazy('lista_materias_admin'))
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')

def cerrar_materias_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            materia_ids = request.POST.getlist('materia_ids')
            cantidad_eliminadas = len(materia_ids)
            print(request.POST)
            if cantidad_eliminadas > 0:
                Materia.objects.filter(id__in=materia_ids).update(inscripcionAbierta=False)
            return redirect(reverse_lazy('lista_materias_admin'))
        else:
            return redirect(reverse_lazy('lista_materias_admin'))
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')
    
def eliminar_mesas_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            mesa_ids = request.POST.getlist('mesa_ids')
            cantidad_eliminadas = len(mesa_ids)
            if cantidad_eliminadas > 0:
                MesaFinal.objects.filter(id__in=mesa_ids).delete()
            mesas = MesaFinal.objects.all()
            return redirect('/mesas_lista')
        return redirect('/mesas_lista')
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')
    
def abrir_mesas_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            mesa_ids = request.POST.getlist('mesa_ids')
            cantidad_eliminadas = len(mesa_ids)
            print(request.POST)
            if cantidad_eliminadas > 0:
                MesaFinal.objects.filter(id__in=mesa_ids).update(inscripcionAbierta=True)
            mesas = MesaFinal.objects.all()
            return redirect('/mesas_lista')
        return redirect('/mesas_lista')
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')
    
def cerrar_mesas_seleccionadas(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            mesa_ids = request.POST.getlist('mesa_ids')
            cantidad_eliminadas = len(mesa_ids)
            print(request.POST)
            if cantidad_eliminadas > 0:
                MesaFinal.objects.filter(id__in=mesa_ids).update(inscripcionAbierta=False)
            mesas = MesaFinal.objects.all()
            return redirect('/mesas_lista')
        return redirect('/mesas_lista')
    elif not request.user.is_staff or not request.user.is_superuser:
        return render(request,'403_forbidden.html')

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
    materia = get_object_or_404(usuarios_materia, pk=id)
    
    if request.user.id == materia.usuario_id and not request.user.is_staff and not request.user.is_superuser:
        if request.method == 'POST':
            # Eliminar inscripciones a finales relacionadas
            InscripcionFinal.objects.filter(
                Q(usuario=request.user) & Q(llamado__materia=materia.materia)
            ).delete()
            
            # Eliminar la inscripción a la materia
            materia.delete()
            return redirect('exito_materia_eliminada_est')
        return render(request, 'materias/eliminar_materia_est.html', {'materia': materia})
    
    elif request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            # Eliminar inscripciones a finales relacionadas
            InscripcionFinal.objects.filter(
                Q(usuario=materia.usuario) & Q(llamado__materia=materia.materia)
            ).delete()
            
            # Eliminar la inscripción a la materia
            materia.delete()
            return redirect('exito_materia_eliminada_adm')
        return render(request, 'materias/eliminar_materia_est.html', {'materia': materia})
    
    else:
        return render(request, '403_forbidden.html')

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

def listar_usuarios_materia(request):
    usuarios_materia_data = usuarios_materia.objects.all()  # Recupera todos los registros de usuarios_materia
    context = {'usuarios_materia_data': usuarios_materia_data}
    return render(request, 'registration/ver_usuarios_materia.html', context)


def validar_inscripcion_final(usuario_id, materia_id):
    # Verificamos si el usuario está inscrito a la materia y su nota de cursada
    try:
        usuario_materia_instance = usuarios_materia.objects.get(
            usuario_id=usuario_id,  # Ajusta si el campo es diferente
            materia_id=materia_id   # Ajusta si el campo es diferente
        )
        nota_cursada = usuario_materia_instance.nota_cursada
        nota_final = usuario_materia_instance.nota_final
        
        if nota_cursada is None or nota_cursada < 7:
            return False
            #JsonResponse({
            #    'puede_inscribirse': False,
            #    'mensaje': 'No tienes la nota de cursada mínima (7) para inscribirte al final.'
            #})
        
        if nota_final is not None:
            return False
            #JsonResponse({
            #    'puede_inscribirse': False,
            #    'mensaje': 'Ya tienes una nota de final registrada para esta materia. No puedes inscribirte nuevamente.'
            #})
    except usuarios_materia.DoesNotExist:
        return False 
        #JsonResponse({
        #    'puede_inscribirse': False,
        #    'mensaje': 'No estás inscrito a esta materia.'
        #})

    # Obtenemos todas las materias correlativas de la materia a la que se quiere inscribir
    correlativas = MateriaCorrelativa.objects.filter(materia_id=materia_id)
    
    # Si no hay correlativas, el usuario puede inscribirse directamente
    if not correlativas.exists():
        return True
        #JsonResponse({
        #    'puede_inscribirse': True,
        #    'mensaje': 'Puedes inscribirte a la mesa final. Esta materia no tiene correlativas.'
        #})

    # Si hay correlativas, verificamos si el usuario ya aprobó todas
    for correlativa in correlativas:
        try:
            correlativa_instance = usuarios_materia.objects.get(
                usuario_id=usuario_id,  # Ajusta si el campo es diferente
                materia_id=correlativa.materia_correlativa_id  # Ajusta si el campo es diferente
            )
            print(correlativa_instance.nota_final)
            
            nota_final = correlativa_instance.nota_final
            if nota_final is None or nota_final < 4:
                return False
                #return JsonResponse({
                #    'puede_inscribirse': False,
                #    'mensaje': f'No has aprobado la materia correlativa {correlativa.materia_correlativa.nombre_materia} con nota 4 o superior.'
                #})
        except usuarios_materia.DoesNotExist:
            print("Nodeberiaperounonuncasabe")
            return False
        #JsonResponse({
        #        'puede_inscribirse': False,
        #        'mensaje': f'No has cursado la materia correlativa {correlativa.materia_correlativa.nombre_materia}.'
        #    })
    
    # Si llegamos aquí, el usuario puede inscribirse
    return True
#JsonResponse({
#        'puede_inscribirse': True,
#        'mensaje': 'Puedes inscribirte a la mesa final.'
#    })

def validar_inscripcion_materias(usuario_id, materia_id):
    try:
        # Verificamos si el usuario está inscrito a la materia
        usuarios_materia.objects.get(
            usuario_id=usuario_id,
            materia_id=materia_id
        )
        return False  # Ya estás inscrito a la materia
    except usuarios_materia.DoesNotExist:
        # El usuario no está inscrito, continuamos con la validación
        pass

    # Obtenemos todas las materias correlativas de la materia a la que se quiere inscribir
    correlativas = MateriaCorrelativa.objects.filter(materia_id=materia_id)

    if not correlativas.exists():
        return True #Se puede inscribir, no hay correlativas
    for correlativa in correlativas:
        try:
            correlativa_instance = usuarios_materia.objects.get(
                usuario_id=usuario_id,
                materia_id=correlativa.materia_correlativa_id  
            )
            
            nota_final = correlativa_instance.nota_final
            if nota_final is None or nota_final < 4:
                return False #No se aprobó final de la correlativa
        except usuarios_materia.DoesNotExist:
            return False #No se curso correlativa
    return True #Se puede inscribir



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

def cargar_nota_final(request, inscripcion_id):
    inscripcion = get_object_or_404(InscripcionFinal, id=inscripcion_id)
    usuario_materia = get_object_or_404(usuarios_materia, usuario=inscripcion.usuario, materia=inscripcion.llamado.materia)

    if request.method == 'POST':
       form = NotaFinalForm(request.POST)
       if form.is_valid():
            nota_final = form.cleaned_data['nota_final']
            usuario_materia.nota_final = nota_final
            usuario_materia.aprobada = nota_final >= 4
            usuario_materia.save()
            inscripcion.aprobada = nota_final >= 4
            inscripcion.save()

            print(f"Nota final: {nota_final}")
            print(f"Aprobada: {inscripcion.aprobada}")

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

def cargar_nota_cursada(request,id):
    usuario_materia = get_object_or_404(usuarios_materia, id=id)

    if request.method == 'POST':
        form = NotaCursadaForm(request.POST)
        if form.is_valid():
            nota_cursada = form.cleaned_data['nota_cursada']
            usuario_materia.nota_cursada = nota_cursada
            usuario_materia.save()

            messages.success(request, f'Nota de cursada cargada correctamente: {nota_cursada}')
            return redirect('/listaMateriasAdm')  # Ajusta esto a tu URL de redirección
    else:
        form = NotaCursadaForm()

    context = {
        'form': form,
        'usuarios_materia': usuario_materia,
    }
    return render(request, 'materias/cargar_nota.html', context)

def editar_notas(request, id):
    usuario_materia = get_object_or_404(usuarios_materia, id=id)

    if request.method == 'POST':
        form = NotaCursadaForm(request.POST, instance=usuario_materia)
        if form.is_valid():
            form.save()
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




def abrir_inscripcion_materia(request,carrera,anio):
    if request.user.is_staff or request.user.is_superuser:
        Materia.objects.filter(carrera_id=carrera,anio=anio).update(inscripcionAbierta=True)
        return redirect('lista_materias_admin')
    else:
        return render(request,"403_forbidden.html")

def cerrar_inscripcion_materia(request,carrera,anio):
    if request.user.is_staff or request.user.is_superuser:
        Materia.objects.filter(carrera_id=carrera,anio=anio).update(InscripcionAbierta=False)
        return redirect('lista_materias_admin')
    else:
        return render(request,"403_forbidden.html")
    
def eliminar_usuarios(request):
    # Restricciones de acceso
    if not (request.user.is_staff or request.user.is_superuser):
        return render(request, '403_forbidden.html', {'error_message': "No tienes permiso para realizar esta acción."})
    
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
                usuarios_eliminados = Usuario.objects.filter(id__in=usuarios_ids)
                cantidad_eliminadas = usuarios_eliminados.count()
                usuarios_eliminados.delete()
                
                messages.success(request, f'Se eliminaron {cantidad_eliminadas} usuarios correctamente.')
            except Exception as e:
                messages.error(request, f'Error al eliminar usuarios: {str(e)}')
        else:
            messages.warning(request, 'No se seleccionaron usuarios para eliminar.')
    
    return redirect('list_user')
    
class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset_form.html'
    email_template_name = 'password_reset_email.html'
    success_url = reverse_lazy('recover_pass.html')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'password_reset_complete.html'
    

def acta_volante(request, final_id):

    pages = []
    finales_inscriptos = InscripcionFinal.objects.filter(llamado=final_id).order_by('usuario__nombre_completo')
    final = get_object_or_404(MesaFinal, id=final_id)
    if finales_inscriptos.count()<=25:
        context = {
            'finales_inscriptos': finales_inscriptos,
            'final': final,
            'cant_inscriptos': finales_inscriptos.count(),
            'piso':0
        }
        return render(request, 'finales/acta_volante.html', context)
    else:
        for i in range(1,ceil(finales_inscriptos.count()/25)+1):
            inscriptos = []
            for inscripto in range(25*(i-1),25*(i-1)+25):
                print(inscripto)
                try:
                    inscriptos.append(finales_inscriptos[inscripto])
                except:
                    pass
            context = {
                'finales_inscriptos': inscriptos,
                'final': final,
                'cant_inscriptos': finales_inscriptos.count(),
                'piso':25*(i-1),
            }
            print(f"fin {i} pagina")
            html = render(request, 'finales/acta_volante.html', context).content.decode('utf-8')
            pages.append({
                'id':f'page_{i}',
                'title':f'Acta volante {i}: {final.materia}',
                'content':html
            })
        pages_json = dumps(pages)
        return render(request, 'finales/lista_acta_volante.html', {'pages_json': pages_json})

def reporte_usuario_materias(request, usuario_id):

    try:
        usuario = Usuario.objects.get(id=usuario_id)
        print(usuario.id)
    except Usuario.DoesNotExist:    
        return HttpResponse("Usuario no encontrado", status=404)
    
    carrera = usuario.carrera 
    # materias_de_carrera = usuarios_materia.objects.filter(carrera = usuario.carrera) #hace falta el total de materias de la carrera, no sólo las inscripciones
    if not carrera:
        return HttpResponse("El usuario no tiene carreras registradas", status=404)

    # Aquí asumimos que solo tomamos la primera carrera, en caso que esté inscripto en más de una carrera
    #carrera = carreras.first()
    # Acceder al número de resolución de la carrera
    #num_resolucion = carrera.num_resolucion if carrera else None

    materias_data = usuarios_materia.objects.filter(usuario=usuario, aprobada=True).values(
        'materia__nombre_materia', 'nota_cursada', 'nota_final', 'materia__anio'
    )
    #total_materias = usuarios_materia.objects.filter(carrera=carrera).count()
    materias_aprobadas = len(materias_data)
    #porcentaje_aprobado = (materias_aprobadas / total_materias) * 100 if total_materias > 0 else 0
   
    materias_por_anio = {}
    for materia in materias_data:
        anio = materia['materia__anio']
        if anio not in materias_por_anio:
            materias_por_anio[anio] = []
        materias_por_anio[anio].append(materia)

     # Obtener la fecha actual para el pie del informe
    fecha_actual = datetime.now()
    dia = fecha_actual.day
    mes = fecha_actual.strftime("%B")  # Nombre del mes
    año = fecha_actual.year

    context = {
        'usuario': usuario,
        'materias_por_anio': materias_por_anio,
       # 'porcentaje_aprobado': porcentaje_aprobado,
       # 'resolucion': usuarios_carreras.num_resolucion,
        'fecha_dia': dia,
        'mes': mes,
        'año': año,
    }
    template = loader.get_template('materias/reporte_usuario_materias.html/')
    html = template.render(context)

    # Convertir HTML a PDF utilizando WeasyPrint con estilos CSS
    css = CSS(string='@page { size: A4; margin: 2cm }')  # Define el tamaño del papel y márgenes
    pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(stylesheets=[css])

#    Generar la respuesta HTTP
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=reporte_usuario_{usuario.nombre_completo}.pdf'
    return response





# También necesitas agregar esta función auxiliar si no existe:
def numero_a_texto(numero):
    """Convierte un número a texto en español"""
    if numero == "-" or numero is None:
        return "-"
    
    try:
        num = float(numero)
        numeros = {
            0: "cero", 1: "uno", 2: "dos", 3: "tres", 4: "cuatro",
            5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez"
        }
        return numeros.get(int(num), str(num))
    except:
        return str(numero)
    

def reporte_estudiante_html(request, usuario_id):
    # Obtener el usuario
    usuario = get_object_or_404(Usuario, id=usuario_id)
    hoy = timezone.now().date()
    
    # Obtener la carrera del usuario (primera carrera si tiene múltiples)
    carrera = usuario.carrera.first()
    if not carrera:
        carrera = Carrera.objects.first()
        if not carrera:
            return HttpResponse("No hay carreras registradas en el sistema", status=404)
    
    # Contar materias aprobadas del usuario
    materias_aprobadas = usuarios_materia.objects.filter(
        usuario_id=usuario_id, 
        aprobada=True
    ).count()
    
    # Obtener todas las materias de la carrera del usuario
    materias_de_carrera = Materia.objects.filter(carrera=carrera)
    
    # Prefetch para optimizar las consultas
    usuarios_materia_prefetch = Prefetch(
        'usuarios_materia_set',
        queryset=usuarios_materia.objects.filter(usuario_id=usuario_id),
        to_attr='usuario_materia'
    )
    
    # Obtener materias por año
    materias_primero = materias_de_carrera.filter(anio=1).prefetch_related(usuarios_materia_prefetch).order_by('nombre_materia')
    materias_segundo = materias_de_carrera.filter(anio=2).prefetch_related(usuarios_materia_prefetch).order_by('nombre_materia')
    materias_tercero = materias_de_carrera.filter(anio=3).prefetch_related(usuarios_materia_prefetch).order_by('nombre_materia')
    materias_cuarto = materias_de_carrera.filter(anio=4).prefetch_related(usuarios_materia_prefetch).order_by('nombre_materia')
    
    # Contar total de materias
    cant_materias = materias_de_carrera.count()
    
    # Función para procesar materias y sus notas
    def procesar_materias(materias):
        return [
            {
                'materia': materia,
                'nota_final': next((um.nota_final for um in materia.usuario_materia if um.usuario_id == usuario_id), "-"),
                'nota_texto': numero_a_texto(next((um.nota_final for um in materia.usuario_materia if um.usuario_id == usuario_id), "-"))
            }
            for materia in materias
        ]
    
    # Procesar materias por año
    materias_primero_con_notas = procesar_materias(materias_primero)
    materias_segundo_con_notas = procesar_materias(materias_segundo)
    materias_tercero_con_notas = procesar_materias(materias_tercero)
    materias_cuarto_con_notas = procesar_materias(materias_cuarto)
    
    # Calcular porcentaje de avance
    if cant_materias > 0:
        porcentaje = round((materias_aprobadas / cant_materias) * 100, 2)
    else:
        porcentaje = 0
    
    # Obtener datos del instituto si existe
    instituto = carrera.instituto if carrera.instituto else None
    
    context = {
        'usuario': usuario,
        'carrera': carrera,
        'instituto': instituto,
        'porcentaje_aprobado': porcentaje,
        'materias_aprobadas': materias_aprobadas,
        'total_materias': cant_materias,
        'materias_primero': materias_primero_con_notas,
        'materias_segundo': materias_segundo_con_notas,
        'materias_tercero': materias_tercero_con_notas,
        'materias_cuarto': materias_cuarto_con_notas,
        'fecha': hoy
    }
    
    return render(request, 'registration/reporte_estudiante_html.html', context)

def numero_a_texto(numero):
    """Convierte un número a texto en español para uso académico"""
    if numero == "-" or numero is None:
        return "-"
    
    try:
        num = float(numero)
        if num == int(num):  # Si es un entero
            num = int(num)
        
        numeros = {
            0: "cero", 1: "uno", 2: "dos", 3: "tres", 4: "cuatro",
            5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez"
        }
        
        if num in numeros:
            return numeros[num]
        else:
            return str(numero)
    except:
        return str(numero)
    


def obtener_finales_estudiante(request):
    """Vista AJAX para obtener finales disponibles para un estudiante específico"""
    if request.method == 'GET':
        estudiante_id = request.GET.get('estudiante_id')
        
        if not estudiante_id:
            return JsonResponse({'status': 'error', 'message': 'ID de estudiante requerido'})
        
        try:
            estudiante = get_object_or_404(Usuario, id=estudiante_id)
            
            # Verificar que sea estudiante
            if estudiante.rol != 'Estudiante':
                return JsonResponse({'status': 'error', 'message': 'El usuario no es un estudiante'})
            
            finales_disponibles = []
            
            # Obtener todas las materias en las que está inscripto el estudiante
            materias_estudiante = usuarios_materia.objects.filter(
                usuario=estudiante,
                aprobada=False  # No ha aprobado aún
            ).select_related('materia')
            
            for inscripcion_materia in materias_estudiante:
                # Verificar requisitos:
                # 1. Nota de cursada >= 7 O modalidad libre
                cumple_nota = (
                    inscripcion_materia.modalidad == 'Libre' or 
                    (inscripcion_materia.nota_cursada is not None and inscripcion_materia.nota_cursada >= 7)
                )
                
                # 2. No tener nota final aprobada
                sin_final_aprobado = (
                    inscripcion_materia.nota_final is None or 
                    inscripcion_materia.nota_final < 4
                )
                
                # 3. Validar correlativas
                cumple_correlativas = validar_inscripcion_final(estudiante_id, inscripcion_materia.materia.id)
                
                # 4. No estar ya inscripto en una mesa final de esta materia
                ya_inscripto = InscripcionFinal.objects.filter(
                    usuario=estudiante,
                    llamado__materia=inscripcion_materia.materia
                ).exists()
                
                if cumple_nota and sin_final_aprobado and cumple_correlativas and not ya_inscripto:
                    # Buscar mesas finales abiertas para esta materia
                    mesas_disponibles = MesaFinal.objects.filter(
                        materia=inscripcion_materia.materia,
                        inscripcionAbierta=True,
                        vigente=True,
                        llamado__gt=timezone.now()  # Fecha futura
                    ).order_by('llamado')
                    
                    for mesa in mesas_disponibles:
                        finales_disponibles.append({
                            'id': mesa.id,
                            'materia': mesa.materia.nombre_materia,
                            'fecha_llamado': mesa.llamado.strftime('%d/%m/%Y %H:%M'),
                            'nota_cursada': inscripcion_materia.nota_cursada or 'Libre',
                            'modalidad': inscripcion_materia.modalidad or 'Regular'
                        })
            
            return JsonResponse({
                'status': 'success',
                'finales': finales_disponibles
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al obtener finales: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})


@csrf_exempt  # TEMPORAL - solo para debugging
def inscribir_final(request):
    """Vista AJAX para realizar la inscripción al final"""
    usuario_id = request.POST.get('usuario')
    llamado_id = request.POST.get('llamado')
    
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
        
        # Verificar que la mesa tenga inscripción abierta
        if not mesa_final.inscripcionAbierta:
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
        InscripcionFinal.objects.create(
            usuario=usuario,
            llamado=mesa_final
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
    Valida si un usuario puede inscribirse al final de una materia
    Retorna True si puede inscribirse, False si no
    """
    try:
        # Verificar si el usuario está inscrito a la materia
        usuario_materia_instance = usuarios_materia.objects.get(
            usuario_id=usuario_id,
            materia_id=materia_id
        )
        
        # Verificar nota de cursada (debe ser >= 7 o estar en modalidad libre)
        if usuario_materia_instance.modalidad != 'Libre':
            if (usuario_materia_instance.nota_cursada is None or 
                usuario_materia_instance.nota_cursada < 7):
                return False
        
        # Verificar que no tenga nota final aprobada
        if (usuario_materia_instance.nota_final is not None and 
            usuario_materia_instance.nota_final >= 4):
            return False
            
    except usuarios_materia.DoesNotExist:
        return False

    # Obtener todas las materias correlativas de la materia
    correlativas = MateriaCorrelativa.objects.filter(materia_id=materia_id)
    
    # Si no hay correlativas, puede inscribirse
    if not correlativas.exists():
        return True

    # Verificar que haya aprobado todas las correlativas
    for correlativa in correlativas:
        try:
            correlativa_instance = usuarios_materia.objects.get(
                usuario_id=usuario_id,
                materia_id=correlativa.materia_correlativa_id
            )
            
            # La correlativa debe estar aprobada (nota final >= 4)
            if (correlativa_instance.nota_final is None or 
                correlativa_instance.nota_final < 4):
                return False
                
        except usuarios_materia.DoesNotExist:
            # No cursó la correlativa
            return False
    
    return True

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


def obtener_contexto_reporte(usuario):
    """
    Función auxiliar para obtener el contexto del reporte
    """
    materias_hardcoded = {
        1: [
            "Ciencia, Tecnología y Sociedad",
            "Inglés I",
            "Álgebra",
            "Algoritmo y Estructura de Datos I",
            "Sistemas y Organizaciones",
            "Arquitectura de Computadoras",
        ],
        2: [
            "Inglés II",
            "Probabilidad y Estadística II",
            "Estadística",
            "Algoritmo y Estructura de Datos II",
            "Sistemas Operativos",
            "Base de Datos",
            "Prácticas Profesionalizantes II",
        ],
        3: [
            "Inglés III",
            "Aspectos Legales de la Profesión",
            "Seminario de Actualización",
            "Redes y Comunicaciones",
            "Ingeniería de Software",
            "Algoritmo y Estructura de Datos III",
            "Prácticas Profesionalizantes III",
        ]
    }
    
    materias_por_anio = {}
    total_materias = 0
    materias_aprobadas = 0
    
    for anio, lista_materias in materias_hardcoded.items():
        materias_por_anio[anio] = []
        
        for nombre_materia in lista_materias:
            total_materias += 1
            
            nota_cursada = "-"
            nota_final = "-"
            calif_cursada = "-"
            calif_final = "-"
            fecha_cursada = "-"
            aprobada = False
            
            try:
                materia = Materia.objects.filter(nombre_materia__iexact=nombre_materia).first()
                if materia:
                    try:
                        inscripcion = usuarios_materia.objects.get(usuario=usuario, materia=materia)
                        
                        if inscripcion.nota_cursada not in [None, '', 'None', 'none']:
                            try:
                                nota_cursada = int(float(inscripcion.nota_cursada))
                                numeros_letras = {
                                    10: "Diez", 9: "Nueve", 8: "Ocho", 7: "Siete",
                                    6: "Seis", 5: "Cinco", 4: "Cuatro", 3: "Tres",
                                    2: "Dos", 1: "Uno"
                                }
                                calif_cursada = numeros_letras.get(nota_cursada, "-")
                            except (ValueError, TypeError):
                                nota_cursada = "-"
                                calif_cursada = "-"
                        
                        if inscripcion.nota_final not in [None, '', 'None', 'none']:
                            try:
                                nota_final = int(float(inscripcion.nota_final))
                                numeros_letras = {
                                    10: "Diez", 9: "Nueve", 8: "Ocho", 7: "Siete",
                                    6: "Seis", 5: "Cinco", 4: "Cuatro", 3: "Tres",
                                    2: "Dos", 1: "Uno"
                                }
                                calif_final = numeros_letras.get(nota_final, "-")
                                
                                if nota_final >= 4:
                                    aprobada = True
                                    materias_aprobadas += 1
                            except (ValueError, TypeError):
                                nota_final = "-"
                                calif_final = "-"
                        
                        if inscripcion.ciclo_lectivo not in [None, '', 'None', 'none']:
                            fecha_cursada = str(inscripcion.ciclo_lectivo)
                        
                        if inscripcion.aprobada and not aprobada:
                            aprobada = True
                            materias_aprobadas += 1
                            
                    except usuarios_materia.DoesNotExist:
                        pass
            except Exception:
                pass
            
            materias_por_anio[anio].append({
                'nombre': nombre_materia,
                'nota_cursada': nota_cursada,
                'nota_final': nota_final,
                'calif_cursada': calif_cursada,
                'calif_final': calif_final,
                'fecha': fecha_cursada
            })
    
    porcentaje_aprobadas = round((materias_aprobadas / total_materias * 100), 2) if total_materias > 0 else 0
    porcentaje_en_letras = numero_a_letras(porcentaje_aprobadas)
    
    return {
        'usuario': usuario,
        'materias_por_anio': materias_por_anio,
        'fecha_actual': now().strftime('%d/%m/%Y'),
        'total_materias': total_materias,
        'materias_aprobadas': materias_aprobadas,
        'porcentaje_aprobadas': porcentaje_aprobadas,
        'porcentaje_en_letras': porcentaje_en_letras
    }


@login_required
def reporte_estudiante_html(request, usuario_id):
    """
    Vista HTML del reporte para previsualización
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)
    
    if not usuario.es_estudiante():
        return HttpResponse("Este reporte solo está disponible para estudiantes", status=403)
    
    context = obtener_contexto_reporte(usuario)
    
    return render(request, 'reportes/constancia_estudiante.html', context)