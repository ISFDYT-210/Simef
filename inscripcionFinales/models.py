from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from .choices import ESTADO_CIVIL_CHOICES, SEXO_CHOICES, MODALIDAD_CHOICES


# === Matriz de capacidades por rol ===========================================
# Única fuente de verdad del "alcance" de cada rol. Para cambiar qué puede
# hacer un rol, se edita SOLO este diccionario.
CAPACIDADES_POR_ROL = {
    'Directivo':  {'gestionar_usuarios', 'gestionar_materias', 'ver_materias',
                   'gestionar_mesas', 'abrir_inscripciones', 'ver_reportes'},
    'Secretario': {'gestionar_usuarios', 'gestionar_materias', 'ver_materias',
                   'gestionar_mesas', 'abrir_inscripciones', 'ver_reportes'},
    'Preceptor':  {'ver_materias', 'gestionar_mesas', 'abrir_inscripciones',
                   'cargar_notas', 'ver_reportes'},
    'Profesor':   {'cargar_notas', 'ver_reportes'},
    'Estudiante': {'inscribirse'},
}


class UsuarioManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Los usuarios deben tener una dirección de email')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField('email', max_length=254, unique=True)
    username = models.CharField('username', unique=True, null=True, max_length=100, blank=False)
    nombre_completo = models.CharField('nombre_completo', max_length=200, null=True, blank=True)
    fecha_nac = models.DateField('fecha_nac', null=True, blank=True)
    dni = models.IntegerField('dni', unique=True, null=True, blank=True)
    direccion = models.CharField('direccion', max_length=50, null=True, blank=True)
    localidad = models.CharField('localidad', max_length=50, null=True, blank=True)
    ciudad = models.CharField('ciudad', max_length=100, null=True, blank=True)
    nacionalidad = models.CharField('nacionalidad', max_length=50, null=True, blank=True)
    telefono_1 = models.CharField('telefono_1', max_length=15, null=True, blank=True)
    telefono_2 = models.CharField('telefono_2', max_length=15, null=True, blank=True)
    estado_civil = models.CharField('estado_civil', choices=ESTADO_CIVIL_CHOICES, max_length=50, null=True, blank=True)
    sexo = models.CharField('sexo', choices=SEXO_CHOICES, max_length=10, null=True, blank=True)
    imagen = models.ImageField('imagenPerfil', upload_to='perfil/', max_length=200, null=True, blank=True)
    is_admin = models.BooleanField('is_admin', default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    carrera = models.ManyToManyField('Carrera', blank=True)
    first_login = models.BooleanField(default=True, help_text="True si es el primer login del usuario")

    # === Roles ===============================================================
    DIRECTIVO = 'Directivo'
    SECRETARIO = 'Secretario'
    PRECEPTOR = 'Preceptor'
    PROFESOR = 'Profesor'
    ESTUDIANTE = 'Estudiante'

    ROL_CHOICES = (
        (DIRECTIVO, 'Director'),
        (SECRETARIO, 'Secretario'),
        (PRECEPTOR, 'Preceptor'),
        (PROFESOR, 'Profesor'),
        (ESTUDIANTE, 'Estudiante'),
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ESTUDIANTE)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.nombre_completo or self.email

    # === Identidad por rol ===================================================
    def es_estudiante(self):
        return self.rol == self.ESTUDIANTE

    def es_profesor(self):
        return self.rol == self.PROFESOR

    def es_directivo(self):
        return self.rol == self.DIRECTIVO

    def es_secretario(self):
        return self.rol == self.SECRETARIO

    def es_preceptor(self):
        return self.rol == self.PRECEPTOR

    def es_super_admin(self):
        return self.is_superuser

    # === Alcance: capacidades ===============================================
    def tiene_capacidad(self, capacidad):
        """El super admin puede todo; el resto, según la matriz de su rol."""
        if self.is_superuser:
            return True
        return capacidad in CAPACIDADES_POR_ROL.get(self.rol, set())

    def puede_gestionar_usuarios(self):
        return self.tiene_capacidad('gestionar_usuarios')

    def puede_gestionar_materias(self):
        return self.tiene_capacidad('gestionar_materias')

    def puede_ver_materias(self):
        return self.tiene_capacidad('ver_materias')

    def puede_gestionar_mesas(self):
        return self.tiene_capacidad('gestionar_mesas')

    def puede_abrir_inscripciones(self):
        return self.tiene_capacidad('abrir_inscripciones')

    def puede_cargar_notas(self):
        return self.tiene_capacidad('cargar_notas')

    def puede_ver_reportes(self):
        return self.tiene_capacidad('ver_reportes')

    def puede_administrar(self):
        """Atajo: ¿es personal administrativo (no estudiante ni profesor)?"""
        return self.is_superuser or self.rol in (self.DIRECTIVO, self.SECRETARIO, self.PRECEPTOR)

    # === Consultas por rol ===================================================
    def puede_cargar_notas_de(self, materia):
        """True si puede cargar notas de ESTA materia en particular."""
        if not self.tiene_capacidad('cargar_notas'):
            return False
        # El super admin siempre puede; el preceptor gestiona todas las materias
        if self.is_superuser or self.es_preceptor():
            return True
        # El profesor, solo las materias que dicta
        if self.es_profesor():
            return materia.profesor_id == self.id
        return False

    def puede_ver_reporte_de(self, estudiante):
        """True si puede ver el reporte/constancia de ESTE estudiante."""
        if self.is_superuser:
            return True
        # Cada usuario puede ver su propio reporte
        if self.id == estudiante.id:
            return True
        if not self.tiene_capacidad('ver_reportes'):
            return False
        # Personal administrativo: cualquier estudiante
        if self.rol in (self.DIRECTIVO, self.SECRETARIO, self.PRECEPTOR):
            return True
        # Profesor: solo estudiantes inscriptos en sus materias
        if self.es_profesor():
            return usuarios_materia.objects.filter(
                usuario=estudiante, materia__profesor=self
            ).exists()
        return False

    @classmethod
    def obtener_profesores(cls):
        return cls.objects.filter(rol=cls.PROFESOR).order_by('nombre_completo')

    @classmethod
    def obtener_estudiantes(cls):
        return cls.objects.filter(rol=cls.ESTUDIANTE).order_by('nombre_completo')

    @classmethod
    def obtener_por_rol(cls, rol):
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


class RegistroAuditoria(models.Model):
    """Registro de acciones importantes: quién hizo qué y cuándo."""
    usuario = models.ForeignKey('Usuario', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='acciones_auditoria')
    accion = models.CharField('Acción', max_length=255)
    modelo_afectado = models.CharField('Modelo', max_length=100, blank=True)
    objeto_id = models.CharField('ID del objeto', max_length=100, blank=True)
    fecha = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'

    def __str__(self):
        quien = self.usuario.email if self.usuario else 'Sistema'
        return f"[{self.fecha:%Y-%m-%d %H:%M}] {quien}: {self.accion}"


# ══════════════════════════════════════════════════════════════════════════
# Inscripción automática a PRIMER AÑO (cursada en bloque).
# Al asignarle una carrera a un ESTUDIANTE, se lo inscribe en todas las
# materias de primer año de esa carrera. Escucha el M2M Usuario.carrera, así
# que cubre todos los flujos (alta individual, carga masiva, admin, etc.).
# ══════════════════════════════════════════════════════════════════════════
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=Usuario.carrera.through)
def inscribir_en_primer_anio(sender, instance, action, pk_set, **kwargs):
    if action != "post_add":
        return
    if not instance.es_estudiante():
        return
    for carrera_id in (pk_set or []):
        for materia in Materia.objects.filter(carrera_id=carrera_id, anio=1):
            usuarios_materia.objects.get_or_create(usuario=instance, materia=materia)
