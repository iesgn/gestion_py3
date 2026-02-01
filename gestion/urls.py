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
from django.contrib import admin

from gestion.views import (
    index, salir, login_view, cambiar_password, cambiar_password_custom, descargar_base_datos,
    cargar_qry, dashboard_jefatura, dashboard_conserjes
)

urlpatterns = [

    path('', index, name='index'),

    path('admin/descargar-db/', descargar_base_datos, name='descargar_base_datos'),
    path('admin/cargar_qry/', cargar_qry, name='cargar_qry'),

    re_path(r'^admin/', admin.site.urls),
    re_path(r'^centro/', include('centro.urls')),
    re_path(r'^convivencia/', include('convivencia.urls')),
    re_path(r'^pdf/', include('pdf.urls')),
    re_path(r'^$',index, name='index'),
    re_path(r'^logout/$',salir),
    # Curro Jul 24:
    re_path(r'^login/$', login_view, name='login'),
    re_path(r'^tde/', include('tde.urls')),
    re_path(r'^absentismo/', include('absentismo.urls')),

    re_path(r'^reservas/', include('reservas.urls')),

    re_path(r'^guardias/', include('guardias.urls')),

    re_path(r'^horarios/', include('horarios.urls')),

    re_path(r'^calendario/', include('calendario.urls')),

    path('carga_archivos/', include('carga_archivos.urls')),

    path('analres/', include('analres.urls')),

    path('DACE/', include('DACE.urls')),
    path('transito/', include('transito.urls')),

    path('permisos/', include('permisos.urls')),

    path('cambiar-password/', cambiar_password, name='cambiar_password'),
    path('cambiar-password-custom/', cambiar_password_custom, name='cambiar_password_custom'),

    path('indexje/', dashboard_jefatura, name='dashboard_jefatura'),

    path('indexcons/', dashboard_conserjes, name='dashboard_conserjes'),



]
