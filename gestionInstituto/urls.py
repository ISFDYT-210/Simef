"""Configuración de URLs del proyecto gestionInstituto.
 
Las rutas de la aplicación viven en inscripcionFinales/urls.py;
acá solo se enchufa el panel de administración y se incluye la app.

El panel de administración solo existe si ADMIN_HABILITADO es True, que por
defecto vale lo mismo que DEBUG: en producción /admin/ responde 404 (#140).
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
 
urlpatterns = [
    path('', include('inscripcionFinales.urls')),
]

if settings.ADMIN_HABILITADO:
    urlpatterns.insert(0, path('admin/', admin.site.urls))
 
# Servir archivos de medios (fotos de perfil, etc.) solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 