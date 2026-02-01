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
	re_path(r'^historial/(?P<alum_id>[0-9]+)/(?P<prof>[a-z]*)$', views.historial),
	re_path(r'^historial_vigente/(?P<alum_id>[0-9]+)/(?P<prof>[a-z]*)$', views.historial_vigente),
	re_path(r'^(?P<tipo>[a-z]+)/(?P<alum_id>[0-9]+)$', views.parte),
	re_path(r'^resumen/', views.resumen, name='resumen'),  # Para GET sin parámetros
    re_path(r'^resumen/(?P<tipo>[a-z]+)/(?P<fecha>[0-9]+)/', views.resumen, name='resumen_con_parametros'),  # Para GET con parámetros
    #re_path(r'^resumen/(?P<tipo>[a-z]+)$', views.resumen),
	#re_path(r'^resumen/(?P<tipo>[a-z]+)/(?P<mes>[0-9]+)/(?P<ano>[0-9]+)$', views.resumen),
	re_path(r'^show/$', views.show, name='show_default'),
	#path('show/<str:tipo>/<int:mes>/<int:ano>/<int:dia>/', views.show, name='show'),
	path('show/<str:tipo>/<int:mes>/<int:ano>/<int:dia>/', views.show, name='show'),
	#re_path(r'^show/(?P<tipo>[a-z]+)/(?P<mes>[0-9]+)/(?P<ano>[0-9]+)/(?P<dia>[0-9]+)$', views.show),
	re_path(r'^estadistica$', views.estadisticas),
	# re_path(r'^alumnadosancionable$', views.alumnadosancionable),
	re_path(r'^estadistica/curso/(?P<curso>[0-9]+)$', views.estadisticas2),
	re_path(r'^grupos', views.grupos),
	re_path(r'^niveles', views.niveles),
	re_path(r'^alumnos', views.alumnos),
	re_path(r'^horas$', views.horas),
    re_path(r'^profesores$', views.profesores),
	re_path(r'^aulaconvivencia$', views.aulaconvivencia),
	# Curro Jul 24: Anado vista para permitir a un profesor anadir un parte
	re_path(r'^profe/(?P<tipo>[a-z]+)/(?P<alum_id>[0-9]+)$', views.parteprofe),

	re_path(r'^misamonestaciones/', views.misamonestaciones, name='misamonestaciones'),

	re_path(r'^amonestacionesprofe/(?P<profe_id>[0-9]+)', views.amonestacionesprofe, name='amonestacionesprofe'),

	re_path(r'^sancionesactivas$', views.sancionesactivas, name='sancionesactivas'),

	path('alumnadosancionable/<ver_ignorados>', views.alumnadosancionable, name='alumnadosancionable'),

	re_path(r'^reincorporacionsanciones$', views.sanciones_reincorporacion, name='sanciones_reincorporacion'),

	path('ignorar/<int:prop_id>/', views.ignorar_propuesta_sancion, name='ignorar'),
	path('reactivar/<int:prop_id>/', views.reactivar_propuesta_sancion, name='reactivar'),
	path('historial_sanciones/<int:alum_id>/', views.historial_sanciones, name='historial_sanciones'),

	path('nueva-intervencion-horizonte/', views.crear_intervencion_horizonte, name='crear_intervencion_horizonte'),

	path('intervenciones-horizonte/', views.listado_intervenciones_horizonte, name='listado_intervenciones_horizonte'),

	path('intervenciones-horizonte/eliminar/', views.eliminar_intervencion_horizonte, name='intervencion_horizonte_eliminar'),

	path('intervenciones-horizonte/<int:pk>/detalle/', views.IntervencionDetalleView.as_view(), name='intervencion_horizonte_detalle'),

	path('derivaciones-aula-horizonte/', views.listado_derivaciones_aula_horizonte, name='listado_derivaciones_aula_horizonte'),

	path('busq-amonestaciones/', views.busq_amonestaciones, name='busq_amonestaciones'),

	path('historico-sanciones/', views.historico_sanciones, name='historico_sanciones'),
]
