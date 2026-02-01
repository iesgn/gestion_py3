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
from .views import busqueda

urlpatterns = [
    path('alumnos', views.alumnos),
    path('alumnos/<int:curso>', views.alumnos_curso),
    path('profesores/change/Baja/<int:codigo>/<str:operacion>', views.profesores_change),
    path('profesores', views.profesores),
    path('cursos', views.cursos),
    path('misalumnos', views.misalumnos),
    path('busqueda/', busqueda, name='busqueda'),

    path('importar_materias/', views.importar_materias, name='importar_materias'),
    path('importar_materias_impartidas/', views.importar_materias_impartidas, name='importar_materias_impartidas'),

    path('importar_matriculas_materias/', views.importar_matriculas_materias, name='importar_matriculas_materias'),

    path('ver_matriculas/', views.ver_matriculas, name='ver_matriculas'),

    path('materias_impartidas/', views.listar_materias_impartidas, name='listar_materias_impartidas'),

    path('importar_libros/', views.importar_libros_texto, name='importar_libros_texto'),

    path('ver_libros/', views.ver_libros_texto, name='ver_libros_texto'),

    # path('revision-libros/', views.seleccionar_revision_view, name='seleccionar_revision_libros'),
    path('revision-libros/<int:profesor_id>/<int:momento_id>/<int:materia_id>/<int:libro_id>/',
         views.revisar_libros_view, name='revisar_libros'),
    path('revision-exitosa/', views.revision_exitosa_view, name='revision_exitosa'),

    path('ajax/materias/', views.obtener_materias_ajax, name='ajax_obtener_materias'),
    path('ajax/libros/', views.obtener_libros_ajax, name='ajax_obtener_libros'),

    path('ajax/get_cursos_profesor/', views.get_cursos_profesor, name='get_cursos_profesor'),
    path('ajax/get_materias_profesor_curso/', views.get_materias_profesor_curso, name='get_materias_profesor_curso'),
    path('ajax/get-libros-materia/', views.get_libros_materia, name='get_libros_materia'),

    path('revision-libros/', views.seleccionar_revision_view, name='revision_libros_inicio'),

    path('revisar-libros/', views.revisar_libros, name='revisar_libros'),
    path('revision-libros/<int:profesor_id>/<int:momento_id>/<int:materia_id>/<int:libro_id>/',
         views.revisar_libros_view, name='revisar_libros'),

    path('revision-libros/get_tabla_revision/', views.get_tabla_revision, name='get_tabla_revision'),

    path('revisar-libros/get_tabla_revision/', views.get_tabla_revision, name='get_tabla_revision'),

    path('revision_exitosa/', views.revision_exitosa_view, name='revision_exitosa'),

    path('guardar_revision_libros/', views.guardar_revision_libros, name='guardar_revision_libros'),

    path('resumen-revisiones/', views.resumen_revisiones, name='resumen_revisiones'),

    path('resumen-revisiones/<int:revision_id>/', views.detalle_revision, name='detalle_revision'),

    path('mis-revisiones-libros/', views.mis_revisiones, name='mis_revisiones'),

    path('revision/editar/<int:revision_id>/', views.editar_revision_libros, name='editar_revision_libros'),

    path('morosos/', views.morosos_view, name='informe_morosos'),
    path('destrozones/', views.destrozones_view, name='informe_destrozones'),

    path('mipreferenciahoraria/', views.mi_preferencia_horaria, name='mi_preferencia_horaria'),

    path('preferenciashorarias/', views.preferencias_profesores, name='preferencias_profesores'),

    path('gestion-sustitutos/', views.crear_sustituto, name='crear_sustituto'),

    path('gestion-sustitutos/lista/', views.lista_sustitutos, name='lista_sustitutos'),
    path('reincorporar-titular/', views.reincorporar_titular, name='reincorporar_titular'),

    path('buscar-libro-olvidado/', views.buscar_revision_libro_olvidado,
     name='buscar_revision_olvidado'),
]
