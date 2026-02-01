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

app_name = 'transito'

urlpatterns = [
    # Vista principal (Pantalla de informe)
    path('informe/', views.gestion_informe_transito, name='gestion_informe'),

    # API AJAX (Backend para el script de JS)
    path('api/check-informe/', views.api_check_informe, name='api_check_informe'),
    path('descargar-informe/', views.DescargarInformePDFView.as_view(), name='descargar_informe'),
    path('rendimiento-departamentos/', views.RendimientoDepartamentosPDFView.as_view(), name='rendimiento_departamentos'),
    path('introducir-historico/', views.IntroducirInformeHistoricoView.as_view(), name='introducir_historico'),
]