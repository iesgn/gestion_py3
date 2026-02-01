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
from .views import EditarHorarioProfesorView, UpdateHorarioView, DeleteHorarioView, CrearItemHorarioView

urlpatterns = [

    re_path(r'^horarioprofe$', views.horario_profesor_view, name='horario_profesor_view'),
    re_path(r'^horariogrupo$', views.horario_curso_view, name='horario_curso_view'),

    path('horarioaula', views.horario_aula_view, name='horario_aula_view'),

    re_path(r'^mihorario$', views.mihorario, name='mihorario'),

    re_path(r'^aulaslibres$', views.aulas_libres, name='aulas_libres'),

    path('profesor/<int:profesor_id>/editar/', EditarHorarioProfesorView.as_view(), name='editar_horario_profesor'),
    path('horario/<int:pk>/editar_item/', UpdateHorarioView.as_view(), name='editar_item_horario'),

    path('item/<int:pk>/eliminar/', DeleteHorarioView.as_view(), name='eliminar_item_horario'),

    path('horario/<int:profesor_id>/crear_item/', CrearItemHorarioView.as_view(), name='crear_item_horario'),

    path('copiar_horario/', views.copiar_horario, name='copiar_horario'),




]
