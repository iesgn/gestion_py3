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
from .views import cerrar_protocolo

urlpatterns = [
        path('misalumnos', views.misalumnos),
        path('alumnos', views.alumnos),
        path('<int:alum_id>/protocolo', views.verprotocolo),
        path('protocolo/<int:proto_id>/nuevaactuacion', views.nuevaactuacion),
        path('protocolo/<int:alum_id>/abrirprotocolo', views.abrirprotocolo),
        path('protocolo/<int:proto_id>/ver', views.verprotocolocerrado),
        path('protocolo/<int:proto_id>/cargarfaltas', views.cargarfaltas),
        path('cerrar_protocolo/', cerrar_protocolo, name='cerrar_protocolo'),
        path('todoalumnado', views.todoalumnado),

]
