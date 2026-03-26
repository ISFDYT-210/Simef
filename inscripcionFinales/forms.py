import csv
from django.shortcuts import render
from django.http import HttpResponse
from django import forms
from django.forms import DateInput
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
#from django.forms import ModelForm, CustomPasswordChangeForm
from .models import *
from django.utils.crypto import get_random_string

validador= RegexValidator(r'^[0-9]*$','Solo se permiten números')

class institutoForms(forms.ModelForm):
      nombre_instituto = forms.CharField(max_length=30)
      email = forms.CharField(max_length=20)
      class Meta:
            model = Instituto
            fields = (
            'nombre_instituto',
            'email_instituto',
            'direccion',
            'localidad',
            'ciudad',
            )


class carreraForm(forms.ModelForm):
      nombre_carrera = forms.CharField( max_length=100)
      num_resolucion = forms.CharField(max_length=100)
      class Meta:
        model = Carrera
        fields =(
          'nombre_carrera',
          'num_resolucion',
          'duracion_carrera',
          'instituto',

        )

class usuarios_materiaForm(forms.ModelForm):
      nombre_materia = forms.CharField( max_length=100)
      # Filtrar solo profesores para el campo profesor
      profesor = forms.ModelChoiceField(
          queryset=Usuario.objects.filter(rol='Profesor'),
          empty_label="Seleccione un profesor",
          required=False
      )
      
      class Meta:
        model = Materia
        fields =(
          'nombre_materia',
          'carrera',
          'profesor'
        )

class materiaCorrelativaForm(forms.ModelForm):
      nombre_materiaCorrelativa = forms.CharField( max_length=100)
      class Meta:
        model = MateriaCorrelativa
        fields =(
          'materia',
          'materia_correlativa'
        )

# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class registri_user_form(UserCreationForm):
    email = forms.EmailField(required=True)
    dni = forms.CharField(max_length=15, validators=[validador])
    
    password1 = None
    password2 = None
    
    # Campos básicos
    username = forms.CharField(max_length=150, required=False, label="Nombre de Usuario")
    nombre_completo = forms.CharField(max_length=100, required=True, label="Nombre Completo")
    fecha_nac = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de nacimiento"
    )
    
    # Datos de ubicación
    direccion = forms.CharField(max_length=200, required=False, label="Dirección")
    localidad = forms.CharField(max_length=100, required=False, label="Localidad")
    ciudad = forms.CharField(max_length=100, required=False, label="Ciudad")
    nacionalidad = forms.CharField(max_length=100, required=False, initial='Argentina', label="Nacionalidad")
    
    # Teléfonos
    telefono_1 = forms.CharField(
        max_length=15, 
        validators=[validador], 
        required=False,
        label="Teléfono"
    )
    telefono_2 = forms.CharField(
        max_length=15, 
        validators=[validador], 
        required=False,
        label="Celular"
    )
    
    # Estado civil y sexo usando los choices correctos
    estado_civil = forms.ChoiceField(
        choices=ESTADO_CIVIL_CHOICES,
        required=False,
        label="Estado civil"
    )
    
    sexo = forms.ChoiceField(
        choices=SEXO_CHOICES,
        required=False,
        label="Sexo"
    )
    
    # Campos específicos por rol
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.all(),
        empty_label="Seleccione una carrera",
        required=False
    )
    especialidad = forms.CharField(max_length=100, required=False)
    cargo = forms.CharField(max_length=100, required=False)
    area = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'nombre_completo', 'dni', 'fecha_nac',
            'direccion', 'localidad', 'ciudad', 'nacionalidad',
            'telefono_1', 'telefono_2', 'estado_civil', 'sexo',
            'rol', 'carrera', 'especialidad', 'cargo', 'area'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generar el password al inicializar el formulario
        self.password_generado = get_random_string(
            length=10, 
            allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        )

    def clean(self):
        cleaned_data = super().clean()
        # Usar el password generado
        cleaned_data['password1'] = self.password_generado
        cleaned_data['password2'] = self.password_generado
        return cleaned_data

    def enviar_credenciales_email(self, usuario, password):
        """Envía las credenciales por email al usuario registrado"""
        try:
            # Contexto para el template del email
            contexto = {
                'usuario': usuario,
                'email': usuario.email,
                'password': password,
                'nombre_completo': usuario.nombre_completo or usuario.username,
                'rol': usuario.get_rol_display() if hasattr(usuario, 'get_rol_display') else usuario.rol,
            }
            
            # Si tienes el template HTML, úsalo
            try:
                html_message = render_to_string('emails/credenciales_usuario.html', contexto)
                plain_message = strip_tags(html_message)
            except:
                # Fallback a mensaje simple si no tienes el template
                plain_message = f"""
Bienvenido/a {contexto['nombre_completo']}!

Tus credenciales de acceso al Sistema Educativo son:

📧 Email: {contexto['email']}
🔑 Contraseña: {contexto['password']}
👤 Rol: {contexto['rol']}

Por favor guarda esta información en un lugar seguro.

Saludos,
Sistema Educativo
                """.strip()
                html_message = None
            
            # Enviar email
            send_mail(
                subject='Credenciales de Acceso - Sistema Educativo',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            print(f"✅ Credenciales enviadas exitosamente a {usuario.email}")
            print(f"   📧 Email: {usuario.email}")
            print(f"   🔑 Password: {password}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email a {usuario.email}: {str(e)}")
            # Mostrar las credenciales en consola como fallback
            print(f"   📧 Email: {usuario.email}")
            print(f"   🔑 Password: {password}")
            return False

    def save(self, commit=True):
        usuario = super().save(commit=False)
        rol = self.cleaned_data.get('rol', '').lower()
        
        # 🔑 CAMBIO PRINCIPAL: Usar el password generado, no el DNI
        print(f"DNI del usuario: {usuario.dni}")
        print(f"Password generado: {self.password_generado}")
        usuario.set_password(self.password_generado)  # ← Usar password generado
        
        # Asignar todos los campos adicionales
        usuario.username = self.cleaned_data.get('username', '')
        usuario.fecha_nac = self.cleaned_data.get('fecha_nac')
        usuario.direccion = self.cleaned_data.get('direccion', '')
        usuario.localidad = self.cleaned_data.get('localidad', '')
        usuario.ciudad = self.cleaned_data.get('ciudad', '')
        usuario.nacionalidad = self.cleaned_data.get('nacionalidad', '')
        usuario.telefono_1 = self.cleaned_data.get('telefono_1', '')
        usuario.telefono_2 = self.cleaned_data.get('telefono_2', '')
        usuario.estado_civil = self.cleaned_data.get('estado_civil', '')
        usuario.sexo = self.cleaned_data.get('sexo', '')
        
        if rol == 'estudiante':
            estudiante = Estudiante.objects.create(
                username=usuario.username,
                email=usuario.email,
                nombre_completo=usuario.nombre_completo,
                dni=usuario.dni,
                fecha_nac=usuario.fecha_nac,
                direccion=usuario.direccion,
                localidad=usuario.localidad,
                ciudad=usuario.ciudad,
                nacionalidad=usuario.nacionalidad,
                telefono_1=usuario.telefono_1,
                telefono_2=usuario.telefono_2,
                estado_civil=usuario.estado_civil,
                sexo=usuario.sexo,
                rol=usuario.rol,
                matricula=get_random_string(length=8, allowed_chars='0123456789')
            )
            estudiante.set_password(self.password_generado)  # ← También para estudiante
            if self.cleaned_data.get('carrera'):
                estudiante.carrera.set([self.cleaned_data['carrera']])
            usuario = estudiante
            
        elif rol == 'profesor':
            usuario = Profesor.objects.create(
                username=usuario.username,
                email=usuario.email,
                nombre_completo=usuario.nombre_completo,
                dni=usuario.dni,
                fecha_nac=usuario.fecha_nac,
                direccion=usuario.direccion,
                localidad=usuario.localidad,
                ciudad=usuario.ciudad,
                nacionalidad=usuario.nacionalidad,
                telefono_1=usuario.telefono_1,
                telefono_2=usuario.telefono_2,
                estado_civil=usuario.estado_civil,
                sexo=usuario.sexo,
                rol=usuario.rol,
                especialidad=self.cleaned_data.get('especialidad', '')
            )
            usuario.set_password(self.password_generado)  # ← También para profesor
            
        elif rol == 'directivo':
            usuario = Directivo.objects.create(
                username=usuario.username,
                email=usuario.email,
                nombre_completo=usuario.nombre_completo,
                dni=usuario.dni,
                fecha_nac=usuario.fecha_nac,
                direccion=usuario.direccion,
                localidad=usuario.localidad,
                ciudad=usuario.ciudad,
                nacionalidad=usuario.nacionalidad,
                telefono_1=usuario.telefono_1,
                telefono_2=usuario.telefono_2,
                estado_civil=usuario.estado_civil,
                sexo=usuario.sexo,
                rol=usuario.rol,
                cargo=self.cleaned_data.get('cargo', '')
            )
            usuario.set_password(self.password_generado)  # ← También para directivo
            
        elif rol == 'preceptor':
            usuario = Preceptor.objects.create(
                username=usuario.username,
                email=usuario.email,
                nombre_completo=usuario.nombre_completo,
                dni=usuario.dni,
                fecha_nac=usuario.fecha_nac,
                direccion=usuario.direccion,
                localidad=usuario.localidad,
                ciudad=usuario.ciudad,
                nacionalidad=usuario.nacionalidad,
                telefono_1=usuario.telefono_1,
                telefono_2=usuario.telefono_2,
                estado_civil=usuario.estado_civil,
                sexo=usuario.sexo,
                rol=usuario.rol,
                area=self.cleaned_data.get('area', '')
            )
            usuario.set_password(self.password_generado)  # ← También para preceptor

        usuario.save()
        
        # 📧 Enviar email con las credenciales después de guardar
        if commit:
            self.enviar_credenciales_email(usuario, self.password_generado)
        
        return usuario


# Tu formulario de perfil se mantiene igual
class profile_students_form(forms.ModelForm):   
    class Meta:
        model = Usuario
        fields = (
            'username',
            'nombre_completo',
            'fecha_nac',
            'dni',
            'direccion',
            'localidad',
            'ciudad',
            'nacionalidad',
            'telefono_1',
            'telefono_2',
            'estado_civil',
            'sexo',
        )
    
    dni = forms.CharField(max_length=15, validators=[validador])
    telefono_1 = forms.CharField(max_length=15, validators=[validador])
    telefono_2 = forms.CharField(max_length=15, validators=[validador])
  
    
class mesa_form(forms.ModelForm):   
  class Meta:
    model = MesaFinal
    fields = (
      'materia',
      'llamado'
    )
    
class edit_profile_form(forms.ModelForm):   
  class Meta:
    model = Usuario
    fields = (
      'username',
      'email',
      'nombre_completo',
      'fecha_nac',
      'dni',
      'direccion',
      'localidad',
      'ciudad',
      'nacionalidad',
      'telefono_1',
      'telefono_2',
      'estado_civil',
      'sexo',
      

    )

class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = '__all__'

class ProfesorForm(forms.ModelForm):
    class Meta: 
        model = Profesor
        fields = '__all__' 

class PreceptorForm(forms.ModelForm):
    class Meta:
        model = Preceptor
        fields = '__all__'
        
class DirectivoForm(forms.ModelForm):
    class Meta:
        model = Directivo 
        fields = '__all__'


############################################################
class MateriaForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios con rol 'Profesor'
        self.fields['profesor'].queryset = Usuario.objects.filter(rol='Profesor')
    
    class Meta:
        model = Materia
        fields = ['nombre_materia', 'carrera', 'profesor', 'anio', 'Horario','inscripcionAbierta']

    # Filtrar solo usuarios con rol de profesor
    profesor = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol='Profesor').order_by('nombre_completo'),
        empty_label="Seleccione un profesor",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Profesor'
    )
    
    class Meta:
        model = Materia
        fields = ['nombre_materia', 'carrera', 'profesor', 'anio', 'dia', 'Horario', 'inscripcionAbierta']
        widgets = {
           'nombre_materia': forms.TextInput(attrs={'class':'form-control'}),
           'carrera': forms.Select(attrs={'class':'form-control'}),
           'anio': forms.Select(attrs={'class':'form-control'}),
           'dia': forms.Select(attrs={'class':'form-control'}),
           'Horario': forms.Select(attrs={'class':'form-control'}),
           'inscripcionAbierta': forms.CheckboxInput(attrs={'class':'form-check-input'})
        }
        labels = {
           'nombre_materia': 'Nombre materia',
           'carrera': 'Carrera',
           'profesor': 'Profesor',
           'anio': 'Año', 
           'dia': 'Día',
           'Horario': 'Horario',
           'inscripcionAbierta': 'Inscripción abierta',
        }

class MesaFinalForm(forms.ModelForm):
    class Meta:
        model = MesaFinal
        fields = ['materia', 'llamado', 'inscripcionAbierta']
        widgets = {
            'llamado': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'inscripcionAbierta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'materia': forms.Select(attrs={'class': 'form-control'})
        }
        labels = {
            'materia': 'Materia',
            'llamado': 'Fecha y Hora del Llamado',
            'inscripcionAbierta': 'Inscripción Abierta'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar el campo llamado para usar datetime-local
        self.fields['llamado'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        
        # Hacer que la materia sea de solo lectura en edición
        if self.instance and self.instance.pk:
            self.fields['materia'].disabled = True

class InscripcionFinalForm(forms.ModelForm):
    class Meta:
        model = InscripcionFinal
        fields = ['usuario', 'llamado']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'llamado': forms.Select(attrs={'class': 'form-control'})
        }
        labels = {
            'usuario': 'Estudiante',
            'llamado': 'Mesa Final'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios con rol 'Estudiante'
        self.fields['usuario'].queryset = Usuario.objects.filter(rol='Estudiante').order_by('nombre_completo')
        
        # Filtrar solo mesas con inscripción abierta y vigentes
        self.fields['llamado'].queryset = MesaFinal.objects.filter(
            inscripcionAbierta=True,
            vigente=True
        ).select_related('materia').order_by('materia__nombre_materia', 'llamado')
        
        # Configurar etiquetas para mostrar información útil
        self.fields['usuario'].empty_label = "Seleccione un estudiante"
        self.fields['llamado'].empty_label = "Seleccione una mesa final"
    
    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get('usuario')
        llamado = cleaned_data.get('llamado')
        
        if usuario and llamado:
            # Verificar que el usuario sea estudiante
            if usuario.rol != 'Estudiante':
                raise forms.ValidationError("Solo los estudiantes pueden inscribirse a mesas finales.")
            
            # Verificar duplicados
            if InscripcionFinal.objects.filter(usuario=usuario, llamado__materia=llamado.materia).exists():
                raise forms.ValidationError(f"El estudiante ya está inscripto a una mesa de {llamado.materia.nombre_materia}")
        
        return cleaned_data


class InscripcionMateriaForm(forms.ModelForm):
    # CORREGIDO: Filtrar SOLO usuarios con rol 'Estudiante' (no superuser)
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol='Estudiante', is_superuser=False).order_by('nombre_completo'),
        empty_label="Seleccione un estudiante",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Estudiante'
    )
    
    # Filtrar solo materias que tengan inscripción abierta
    materia = forms.ModelChoiceField(
        queryset=Materia.objects.filter(inscripcionAbierta=True).order_by('nombre_materia'),
        empty_label="Seleccione una materia",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Materia'
    )
    
    # Usar las opciones correctas de modalidad
    modalidad = forms.ChoiceField(
        choices=[('', 'Seleccione modalidad')] + list(MODALIDAD_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Modalidad',
        required=False
    )
    
    # Campo institución como input manual - SOLO REQUERIDO para Itinerante
    institucion = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese la institución (Solo en modalidad Itinerante)'
        }),
        label='Institución (Solo en modalidad Itinerante)'
    )
    
    # Campo turno con opciones predefinidas - SOLO REQUERIDO para Itinerante
    turno = forms.ChoiceField(
        choices=[('', 'Seleccione turno (Solo en modalidad Itinerante)')] + [('Mañana','Mañana'), ('Tarde','Tarde'), ('Noche','Noche')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Turno (Solo en modalidad Itinerante)',
        required=False
    )
    
    class Meta:
        model = usuarios_materia
        fields = ['usuario', 'materia', 'modalidad', 'institucion', 'turno']
        labels = {
            'usuario': 'Estudiante',
            'materia': 'Materia',
            'modalidad': 'Modalidad',
            'institucion': 'Institución (Solo en modalidad Itinerante)',
            'turno': 'Turno (Solo en modalidad Itinerante)'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        modalidad = cleaned_data.get('modalidad')
        institucion = cleaned_data.get('institucion')
        turno = cleaned_data.get('turno')
        
        # Validar que si la modalidad es "Itinerante", institución y turno sean requeridos
        if modalidad == 'Itinerante':
            if not institucion:
                self.add_error('institucion', 'Este campo es requerido para la modalidad Itinerante.')
            if not turno:
                self.add_error('turno', 'Este campo es requerido para la modalidad Itinerante.')
        
        return cleaned_data

class NotaFinalForm(forms.Form):
    nota_final = forms.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)

class NotaCursadaForm(forms.ModelForm):
    class Meta:
        model = usuarios_materia
        fields = ('nota_cursada', 'nota_final')
        widgets = {
            'nota_cursada': forms.NumberInput(attrs={'min': '0', 'max': '10'}),
            'nota_final': forms.NumberInput(attrs={'min': '0', 'max': '10'}),
        }

    def clean_nota_cursada(self):
        nota = self.cleaned_data.get('nota_cursada')
        if nota is not None:
            if nota < 0 or nota > 10:
                raise forms.ValidationError("La nota debe estar entre 0 y 10.")
        return nota

    def clean_nota_final(self):
        nota = self.cleaned_data.get('nota_final')
        if nota is not None:
            if nota < 0 or nota > 10:
                raise forms.ValidationError("La nota debe estar entre 0 y 10.")
        return nota

    def clean(self):
        cleaned_data = super().clean()
        nota_cursada = cleaned_data.get('nota_cursada')
        nota_final = cleaned_data.get('nota_final')
        
        # Obtener la modalidad del objeto actual si existe
        if self.instance and hasattr(self.instance, 'modalidad'):
            modalidad = self.instance.modalidad
            
            print(f"DEBUG - Modalidad encontrada: '{modalidad}'")
            
            # Para modalidad "Regular" o "Itinerante" validar la regla
            # Verificar tanto el valor como el código numérico si existe
            modalidades_con_restriccion = ['Regular', 'Itinerante', '02', '03', 2, 3]  # Agregar posibles códigos
            
            if modalidad in modalidades_con_restriccion:
                # Obtener el valor actual de nota_cursada: del formulario o de la BD
                nota_cursada_final = nota_cursada if nota_cursada is not None else getattr(self.instance, 'nota_cursada', None)
                
                print(f"DEBUG - Modalidad requiere validación: {modalidad}")
                print(f"DEBUG - Nota cursada final considerada: {nota_cursada_final}")
                print(f"DEBUG - ¿Se está intentando cargar nota final? {nota_final is not None}")
                print(f"DEBUG - ¿Hay nota cursada? {nota_cursada_final is not None}")
                
                # Si se está intentando cargar nota final pero no hay nota cursada
                if nota_final is not None and nota_cursada_final is None:
                    print("DEBUG - DISPARANDO VALIDACIÓN")
                    # Mostrar el nombre legible de la modalidad
                    nombre_modalidad = "Regular/Itinerante" if str(modalidad) in ['02', '03', '2', '3'] else modalidad
                    raise forms.ValidationError(
                        f'Para la modalidad "{nombre_modalidad}" debe cargar primero la nota de cursada antes de la nota final.'
                    )
        
        return cleaned_data
    
    

class InscripcionFinalForm(forms.ModelForm):
    # Filtrar solo usuarios con rol de estudiante
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol='Estudiante').order_by('nombre_completo'),
        empty_label="Seleccione un estudiante",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Estudiante'
    )
    
    # Filtrar solo mesas finales con inscripción abierta
    llamado = forms.ModelChoiceField(
        queryset=MesaFinal.objects.filter(inscripcionAbierta=True, vigente=True).order_by('materia__nombre_materia', 'llamado'),
        empty_label="Seleccione una mesa final",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Mesa Final'
    )
    
    class Meta:
        model = InscripcionFinal
        fields = ['usuario', 'llamado']
        widgets = {
            'aprobada': forms.HiddenInput(),  # Ocultar el campo aprobada
        }
        labels = {
            'usuario': 'Estudiante',
            'llamado': 'Mesa Final'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar la representación de las opciones de llamado
        self.fields['llamado'].queryset = MesaFinal.objects.filter(
            inscripcionAbierta=True, 
            vigente=True
        ).select_related('materia').order_by('materia__nombre_materia', 'llamado')
        
        # Personalizar cómo se muestran las opciones
        choices = [('', 'Seleccione una mesa final')]
        for mesa in self.fields['llamado'].queryset:
            fecha_str = mesa.llamado.strftime('%d/%m/%Y %H:%M')
            choice_text = f"{mesa.materia.nombre_materia} - {fecha_str}"
            choices.append((mesa.pk, choice_text))
        
        self.fields['llamado'].choices = choices

class FiltroInscripcionForm(forms.Form):
    estudiante = forms.CharField(required=False)
    materia = forms.CharField(required=False)

# En forms.py
class ArchivoForm(forms.Form):
    csv_file = forms.FileField(
        label='Seleccione un archivo csv', 
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        
        # Validar tamaño del archivo (5MB máximo)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('El archivo no puede ser mayor a 5MB.')
        
        # Validar extensión
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('Solo se permiten archivos CSV.')
        
        return file