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

app_name = 'permisos'

urlpatterns = [
    # Vista para jefatura: registrar solicitudes
    path('asuntos-propio/crear/', views.crear_asunto_propio, name='crear_asunto_propio'),

    # API JSON para calendario profesores (lectura pública)
    path('api/asuntos-propio/', views.api_asuntos_propios_calendar, name='api_asuntos_propios_calendar'),

    # Calendario público para profesores
    path('asuntos-propio/calendario/', views.calendario_asuntos_propios, name='calendario_asuntos_propios'),

    # Opcional: lista de todas las solicitudes (solo jefatura)
    path('asuntos-propio/lista/', views.lista_asuntos_propios, name='lista_asuntos_propios'),

    path('eliminar/', views.eliminar_asunto_propio, name='eliminar_asunto_propio'),

]
