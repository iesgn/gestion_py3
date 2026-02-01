"""
╔════════════════════════════════════════════════════════════════════════════╗
║                          GESTION@ - GESTIÓN DE CENTROS EDUCATIVOS         ║
║                                                                            ║
║ Copyright © 2023-2026 Francisco Fornés Rumbao, Raúl Reina Molina          ║
║                          Proyecto base por José Domingo Muñoz Rodríguez    ║
║                                                                            ║
║ Todos los derechos reservados. Prohibida la reproducción, distribución,   ║
║ modificación o comercialización sin consentimiento expreso de los autores. ║
║                                                                            ║
║ Este archivo es parte de la aplicación Gestion@.                          ║
║                                                                            ║
║ Para consultas sobre licencias o permisos:                                ║
║ Email: fforrum559@g.educaand.es                                           ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

from django.urls import re_path, path

from . import views
from .views import eliminar_incidencia, actualizar_incidencia

urlpatterns = [

    re_path(r'^incidenciaticprofe$', views.incidenciaticprofe, name='incidenciaticprofe'),
    re_path(r'^misincidenciastic$', views.misincidenciastic, name='misincidenciastic'),
    re_path(r'^incidenciastic$', views.incidenciastic, name='incidenciastic'),
    path('eliminar_incidencia/', eliminar_incidencia, name='eliminar_incidencia'),
    path('actualizar_incidencia/', actualizar_incidencia, name='actualizar_incidencia'),


]
