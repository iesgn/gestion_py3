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

urlpatterns = [

    re_path(r'^parteguardias$', views.parteguardias, name='parteguardias'),
    re_path(r'^misausencias$', views.misausencias, name='misausencias'),

    re_path(r'^estadisticas', views.estadisticas, name='estadisticas'),

    path('horario-profesor-ajax/', views.horario_profesor_ajax, name='horario_profesor_ajax'),

    path('guardar_guardias_ajax/', views.guardar_guardias_ajax, name='guardar_guardias_ajax'),

    path('obtener_itemguardia_por_fecha/', views.obtener_itemguardia_por_fecha, name='obtener_itemguardia_por_fecha'),

    path('obtener_itemguardia_por_fecha_y_profe/', views.obtener_itemguardia_por_fecha_y_profe, name='obtener_itemguardia_por_fecha_y_profe'),

    path('parteguardias_ajax/', views.parteguardias_ajax, name='parteguardias_ajax'),

    #path('confirmar_guardia_ajax/', views.confirmar_guardia_ajax, name='confirmar_guardia_ajax'),

    path('obtener-profesores/', views.obtener_profesores, name='obtener_profesores'),

    path('ver-guardias/', views.verausencias, name='verausencias'),
    path('guardia/<int:pk>/editar/', views.editar_item_guardia, name='editar_item_guardia'),
    path('guardia/<int:pk>/borrar/', views.borrar_item_guardia, name='borrar_item_guardia'),

    path('eliminar_itemguardia_por_fecha/', views.eliminar_itemguardia_por_fecha, name='eliminar_itemguardia_por_fecha'),

    path('eliminar_itemguardia_por_fecha_y_profe/', views.eliminar_itemguardia_por_fecha_y_profe, name='eliminar_itemguardia_por_fecha_y_profe'),

    path('eliminar_itemguardia_por_fecha_profe_y_tramo/', views.eliminar_itemguardia_por_fecha_profe_y_tramo,
         name='eliminar_itemguardia_por_fecha_profe_y_tramo'),

    path('obtener_tramos_guardia_por_fecha/', views.obtener_tramos_guardia_por_fecha, name='obtener_tramos_guardia_por_fecha'),

    path('horario_guardia_ajax/', views.horario_guardia_ajax, name='horario_guardia_ajax'),

    path('actualizar_ausencias_ajax/', views.actualizar_ausencias_ajax, name='actualizar_ausencias_ajax'),

    path('actualizar_guardia_ajax/', views.actualizar_guardia_ajax, name='actualizar_guardia_ajax'),

    path("modal/registrar_ausencia/", views.modal_registrar_ausencia, name="modal-registrar-ausencia"),

]
