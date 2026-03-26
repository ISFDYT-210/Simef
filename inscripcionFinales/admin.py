from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from inscripcionFinales import *
from .models import Carrera, Usuario,Instituto, Materia, MateriaCorrelativa
from inscripcionFinales.models import Instituto, Usuario, Materia, MateriaCorrelativa, usuarios_materia, MesaFinal, InscripcionFinal, Estudiante, Profesor

# Register your models here.

class UsuarioAdmin(UserAdmin):
  list_display = ('email', 'username')
  search_fields = ('email', 'username')
  readonly_fields = ['id']

  filter_horizontal = ()
  list_filter = ()
  fieldsets = ()

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Instituto)
admin.site.register(Carrera)
admin.site.register(Materia)
admin.site.register(MateriaCorrelativa)
admin.site.register(usuarios_materia)
admin.site.register(MesaFinal)
admin.site.register(InscripcionFinal)
admin.site.register(Estudiante)
