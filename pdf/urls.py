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
    re_path(r'^partes/(?P<curso>[0-9]+)$', views.imprimir_partes),
    re_path(r'^telefono/(?P<curso>[0-9]+)$', views.imprimir_telefonos),
    re_path(r'^historial/(?P<alum_id>[0-9]+)/(?P<prof>[a-z]*)$', views.imprimir_historial),
    re_path(r'^show/(?P<tipo>[a-z]+)/(?P<mes>[0-9]+)/(?P<ano>[0-9]+)/(?P<dia>[0-9]+)$', views.imprimir_show),
    re_path(r'^send/amonestacion/(?P<mes>[0-9]+)/(?P<ano>[0-9]+)/(?P<dia>[0-9]+)$', views.send_amonestacion),
    re_path(r'^carta_amonestacion/(?P<mes>[0-9]+)/(?P<ano>[0-9]+)/(?P<dia>[0-9]+)/(?P<todos>[a-z]+)$', views.carta_amonestacion),
    re_path(r'^carta_sancion/(?P<identificador>[0-9]+)$', views.carta_sancion),
    re_path(r'^profesores$', views.imprimir_profesores),
    re_path(r'^claustro$', views.imprimir_profesores),
    re_path(r'^semana$', views.imprimir_profesores),
    re_path(r'^sanciones/hoy$', views.imprimir_sanciones_hoy),
    path('infoIA/<int:alum_id>', views.infoIA),

    re_path(r'^carta_abs_tutor/(?P<proto_id>[0-9]+)$', views.carta_abs_tutor_familia),
    re_path(r'^carta_abs_ED/(?P<proto_id>[0-9]+)$', views.carta_abs_tutor_ED),
    re_path(r'^carta_abs_familia_ED/(?P<proto_id>[0-9]+)$', views.carta_abs_ED_familia),

    path('revision-libros/hoja_firmas_pdf/', views.hoja_firmas_revision_libros, name='hoja_firmas_revision_libros')


]
