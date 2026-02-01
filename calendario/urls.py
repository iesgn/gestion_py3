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
    path('faltas/<int:proto_id>/', views.faltas, name='faltas'),

    path('faltas_json/<int:proto_id>/', views.faltas_json, name='faltas_json'),

    path('amonestaciones/<int:alum_id>/', views.amonestaciones, name='amonestaciones'),

    path('amonestaciones_json/<int:alum_id>', views.amonestaciones_json, name='amonestaciones_json'),

]