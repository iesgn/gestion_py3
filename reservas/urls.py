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

from reservas import views
from reservas.views import filter_reservables, eliminar_reserva

urlpatterns = [

    re_path(r'^verreservas$', views.reservas, name='verreservas'),
    re_path(r'^verreservascal$', views.reservascal, name='verreservascal'),

    path('reservaprofe', views.crear_reserva_profe, name='reservaprofe'),

    path('reserva', views.crear_reserva, name='reserva'),


    re_path(r'^misreservas$', views.misreservas, name='misreservas'),

    path('filter_reservables/', filter_reservables, name='filter_reservables'),
    path('verificar-disponibilidad/', views.verificar_disponibilidad, name='verificar_disponibilidad'),

    path('eliminar_reserva/', eliminar_reserva, name='eliminar_reserva'),

    path('json/', views.reservas_json, name='reservas_json'),




]
