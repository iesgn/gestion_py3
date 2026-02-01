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

from django.urls import path
from . import views

urlpatterns = [
    path('crear_actividad/', views.crear_actividad, name='crear_actividad'),
    path('misactividades/', views.misactividades, name='misactividades'),
    path('actividadesdace/', views.actividadesdace, name='actividadesdace'),
    path('actividad/<int:actividad_id>/editar/', views.editar_actividad, name='editar_actividad'),

    path('actividad/<int:actividad_id>/detalles/', views.detalles_actividad, name='detalles_actividad'),

    path('actividad/<int:actividad_id>/editar_participantes/', views.editar_actividad_participantes,
         name='editar_actividad_participantes'),

    path('actividad/<int:actividad_id>/editar_economica/', views.editar_actividad_economica,
         name='editar_actividad_economica'),
    path('get-alumnos-unidad/<int:unidad_id>/', views.get_alumnos_unidad, name='get_alumnos_unidad'),

    path('get-alumnos-participantes-unidad/<int:unidad_id>/<int:actividad_id>/', views.get_alumnos_participantes_unidad,
         name='get_alumnos_participantes_unidad'),
    path('aprobar_actividad/<int:actividad_id>/', views.aprobar_actividad, name='aprobar_actividad'),
    # path('calendario_actividades/', views.calendario_actividades, name='calendario_actividades'),

    path('json/', views.actividadesdace_json, name='actividadesdace_json'),

    path("calendario/", views.actividades_calendario, name="actividades_calendario"),

    path('desaprobar_actividad/<int:actividad_id>/', views.desaprobar_actividad, name='desaprobar_actividad'),
    path('borrar_actividad/<int:actividad_id>/', views.borrar_actividad, name='borrar_actividad'),
]
