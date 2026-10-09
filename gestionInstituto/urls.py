"""Configuración de URLs del proyecto gestionInstituto.
 
Las rutas de la aplicación viven en inscripcionFinales/urls.py;
acá solo se enchufa el panel de administración y se incluye la app.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inscripcionFinales.urls')),
]
 
# Servir archivos de medios (fotos de perfil, etc.) solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 