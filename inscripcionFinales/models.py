from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager, Group, PermissionsMixin, AbstractUser, User,)
from django.db import models
from django.utils.timezone import now
from .choices import ESTADO_CIVIL_CHOICES,SEXO_CHOICES,MODALIDAD_CHOICES
import random
#from django.contrib.auth.forms import PasswordChangeForm


class UsuarioManager(BaseUserManager):
    
    def create_user(self ,email, password, **extra_fields):
        if not email:
            raise ValueError('Los usuarios deben tener una direccion de email')

        user =self.model(
          email= self.normalize_email(email),
          
        )
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
        
    def create_superuser(self, email, password, **extra_fields):
        user = self.create_user(
          email = self.normalize_email(email),
          password = password,
        )
        user.is_superuser = True
        user.is_admin = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class Usuario(AbstractBaseUser,PermissionsMixin):
      
    email = models.EmailField('email', max_length=254, unique = True)
    username = models.CharField('username',unique = True,null = True, max_length=100, blank=False)
    nombre_completo = models.CharField('nombre_completo', max_length=200, null=True, blank=True)
    fecha_nac = models.DateField('fecha_nac', null=True, blank=True)
    dni = models.IntegerField('dni',unique = True, null= True, blank=True)
    direccion = models.CharField('direccion', max_length=50, null=True, blank=True)
    localidad = models.CharField('localidad', max_length=50, null=True, blank=True)
    ciudad = models.CharField('ciudad', max_length=100, null=True, blank=True)
    nacionalidad = models.CharField('nacionalidad',max_length=50, null=True, blank=True)
    telefono_1 = models.IntegerField('telefono_1', null=True, blank=True)
    telefono_2 = models.IntegerField('telefono_2', null=True, blank=True)
    estado_civil=models.CharField('estado_civil', choices=ESTADO_CIVIL_CHOICES,max_length=50, null=True, blank=True)
    sexo=models.CharField('sexo',choices=SEXO_CHOICES,max_length=10, null=True, blank=True)
    imagen = models.ImageField('imagenPerfil', upload_to='perfil/', max_length=200, null=True, blank=True)
    is_admin = models.BooleanField('is_admin', default=False)
    is_superuser = models.BooleanField('is_superuser', default=False)
    is_active = models.BooleanField(default = True)
    is_staff = models.BooleanField(default = False)
    carrera = models.ManyToManyField('Carrera',blank=True)
    first_login = models.BooleanField(default=True, help_text="True si es el primer login del usuario")
    Estudiante = 'Estudiante'          
    Preceptor = 'Preceptor'
    Profesor = 'Profesor'
    Directivo = 'Directivo'
    Administrador = 'Administrador'
    Bibliotecario = 'Bibliotecario'
    

    ROL_CHOICES = (
        (Directivo, 'Directivo'),
        (Preceptor, 'Preceptor'),
        (Profesor, 'Profesor'),
        (Estudiante, 'Estudiante'),
        (Administrador, 'Administrador'),
        (Bibliotecario, 'Bibliotecario'),

        
     )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=Estudiante)
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password']

    
    def __str__(self):
        if self.nombre_completo: 
            return self.nombre_completo
        else:
            return self.email
        
    def es_estudiante(self):
        """Verifica si el usuario es estudiante"""
        return self.rol == 'Estudiante'
    
    def es_profesor(self):
        """Verifica si el usuario es profesor"""
        return self.rol == 'Profesor'
    
    def es_directivo(self):
        """Verifica si el usuario es directivo"""
        return self.rol == 'Directivo'
    
    def es_preceptor(self):
        """Verifica si el usuario es preceptor"""
        return self.rol == 'Preceptor'
    
    def es_administrador(self):
        """Verifica si el usuario es administrador"""
        return self.rol == 'Administrador'
    
    def es_bibliotecario(self):
        """Verifica si el usuario es bibliotecario"""
        return self.rol == 'Bibliotecario'
    
    def puede_ensenar(self):
        """Verifica si el usuario puede enseñar materias"""
        return self.es_profesor() or self.is_staff or self.is_superuser
    
    def puede_inscribirse_materias(self):
        """Verifica si el usuario puede inscribirse en materias"""
        return self.es_estudiante()
    
    def puede_administrar(self):
        """Verifica si el usuario puede realizar tareas administrativas"""
        return self.es_directivo() or self.es_preceptor() or self.is_staff or self.is_superuser
    
    @classmethod
    def obtener_profesores(cls):
        """Método de clase para obtener todos los profesores"""
        return cls.objects.filter(rol='Profesor').order_by('nombre_completo')
    
    @classmethod
    def obtener_estudiantes(cls):
        """Método de clase para obtener todos los estudiantes"""
        return cls.objects.filter(rol='Estudiante').order_by('nombre_completo')
    
    @classmethod
    def obtener_por_rol(cls, rol):
        """Método de clase para obtener usuarios por rol específico"""
        return cls.objects.filter(rol=rol).order_by('nombre_completo')

    


class Carrera(models.Model):
    nombre_carrera = models.CharField('nombre_carrera',unique = True, max_length=100)
    num_resolucion = models.CharField('num_resolucion', max_length=100, blank = True, null = True)
    duracion_carrera = models.PositiveBigIntegerField(default=3)
    instituto = models.ForeignKey('Instituto',on_delete=models.CASCADE,null=True)
    
    def __str__(self):
        return self.nombre_carrera
    
    

class usuarios_carreras(models.Model):
    carreras = models.ManyToManyField('Carrera', blank=False)
    usuario= models.ManyToManyField('Usuario', blank=False)
    
class materia_carrera(models.Model):
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE, null=True)
    carrera = models.ForeignKey('Carrera', on_delete=models.CASCADE, null=True)

class Instituto(models.Model):
    nombre_instituto = models.CharField('nombre_instituto',unique = True, max_length=100)
    email_instituto = models.EmailField('email_instituto', max_length=254, unique = True)
    direccion=models.CharField('direccion', max_length=50)
    localidad=models.CharField('localidad', max_length=50)
    ciudad=models.CharField('ciudad', max_length=100)
    telefono_1 = models.IntegerField('telefono_1')
    telefono_2 = models.IntegerField('telefono_2')
    
    imagen = models.ImageField('imagenPerfil', upload_to='perfil/', max_length=200,blank = True,null = True)
    
    def __str__(self):
        return self.nombre_instituto


class Materia(models.Model):
    nombre_materia = models.CharField('nombre_materia', max_length=50)
    carrera = models.ForeignKey('Carrera', on_delete=models.CASCADE, null=True)
    profesor = models.ForeignKey('Usuario', on_delete=models.CASCADE, null=True)
    inscripcionAbierta = models.BooleanField(default=False)

    Inicio = '12:00'
    Inicio1 = '14:00'
    Inicio2 = '16:00'
    Inicio3 = '18:00'
    Inicio4 = '20:00'
    
    HORARIO_CHOICES = ( 
        
        ('12:00', '12:00'),
        ('14:00', '14:00'),
        ('16:00', '16:00'),
        ('18:00', '18:00'),
        ('20:00', '20:00')
        )
   
    Horario=models.CharField(max_length=22, choices=HORARIO_CHOICES, default='12:00')   
       
    ANIO_CHOICES = (
             
        (1, '1'),
        (2, '2'),
        (3, '3'), 
        (4, '4'),       
     )
    anio=models.IntegerField(choices=ANIO_CHOICES, default=1)

    DIA_CHOICES = (
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
    )
    dia = models.CharField(max_length=20, choices=DIA_CHOICES, default='Lunes')
    
    def __str__(self):
        return self.nombre_materia

    


class MateriaCorrelativa(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='materias_correlativas')
    materia_correlativa = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='correlativas_de')

    def __str__(self):
        return f"{self.materia} -> {self.materia_correlativa}"

class usuarios_materia(models.Model):
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE, null=False, blank=False)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, null=False, blank=False)  # 'Usuario' con mayúscula
    nota_cursada = models.FloatField('Nota de Cursada', null=True, blank=True)
    nota_final = models.FloatField('Nota de Final', null=True, blank=True)
    aprobada = models.BooleanField(default=False)
    condicional = models.BooleanField(default=False)
    modalidad = models.CharField('Modalidad', choices=MODALIDAD_CHOICES, max_length=20, null=True, blank=True)
    ciclo_lectivo = models.CharField('Ciclo lectivo', null=True, blank=True, max_length=100)
    
    # Nuevos campos agregados
    institucion = models.CharField('Institución', max_length=100, blank=True, null=True)
    
    TURNO_CHOICES = (
        ('Mañana','Mañana'),
        ('Tarde','Tarde'),
        ('Noche','Noche')
    )
    turno = models.CharField('Turno', max_length=20, choices=TURNO_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.materia} -> {self.usuario}"
    
    def puede_inscribirse_en_una_materia(self):
        return ((self.nota_cursada >= 4 and self.nota_cursada is not None ) or self.modalidad == 'Libre') and self.aprobada == False
    
    def puede_inscribirse_en_mesa_final(self):
        return ((self.nota_cursada >= 4 and self.nota_cursada is not None ) or self.modalidad == 'Libre') and self.aprobada == False
    
class MesaFinal(models.Model):
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE, blank=False, null=False)
    llamado= models.DateTimeField('Llamado', null=False, blank=False) 
    vigente= models.BooleanField(default=True)
    inscripcionAbierta = models.BooleanField(default=False) 
    def __str__(self):
        return f"{self.materia} -> {self.llamado}"

class InscripcionFinal(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, blank=False, null=False)  # 'Usuario' con mayúscula
    llamado = models.ForeignKey('MesaFinal', on_delete=models.CASCADE, blank=False, null=False)
    aprobada= models.BooleanField(null=True) 
    inscripcionAbierta=models.BooleanField(default=False)

class Estudiante(Usuario):
    matricula= models.CharField(max_length=10,unique=True)

class Profesor(Usuario):
    especialidad = models.CharField(max_length=100)

class Directivo(Usuario):
    cargo = models.CharField(max_length=100)

class Preceptor(Usuario):
    area = models.CharField(max_length=100)
