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

from django.urls import include, re_path, path
from . import views

urlpatterns = [
    path('calificaciones/', views.calificaciones, name='calificaciones'),
    path('calificaciones/procesar/', views.calificaciones_procesar_datos, name='calificaciones_procesar_datos'),
    path('RegAlum/', views.regalum, name='RegAlum'),
    path('RegAlum/procesar/', views.RegAlum_procesar_datos, name='RegAlum_procesar_datos'),
    path('admision/', views.admision, name='admision'),
    path('admision/procesar/', views.admision_procesar_datos, name='admision_procesar'),
]