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

import datetime
import time,calendar

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from centro.models import Profesores
from centro.utils import get_current_academic_year, get_previous_academic_years
from centro.views import group_check_prof, group_check_tde
from tde.forms import IncidenciaTicProfeForm
from tde.models import IncidenciasTic
from django.core.mail import send_mail


# Create your views here.

@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def incidenciaticprofe(request):
    profesor = request.user.profesor
    titulo = "Incidencias TIC"

    if request.method == 'POST':
        form = IncidenciaTicProfeForm(request.POST)
        if form.is_valid():
            try:
                incidencia = form.save()
                aula = incidencia.aula
                profesores_en_aula = Profesores.objects.filter(itemhorario__aula=aula).distinct()

                template = get_template("correo_nueva_incidencia.html")
                contenido = template.render({'inc': incidencia})
                correos = []
                for prof in profesores_en_aula:
                    correo = Profesores.objects.get(id=prof.id).Email
                    if correo != "":
                        correos.append(correo)

                send_mail(
                    'Nueva Incidencia TIC',
                    contenido,
                    '41011038.jestudios.edu@juntadeandalucia.es',
                    correos,
                    fail_silently=False,
                )


            except IntegrityError:
                print("Ya existe una Incidencia TIC igual")

            return redirect('/tde/misincidenciastic')
        else:
            print(form.errors)
    else:
        form = IncidenciaTicProfeForm(
            initial={'fecha': time.strftime("%d/%m/%Y"), 'profesor': profesor.id}
        )

        titulo = "Incidencias TIC"

    context = {'form': form, 'titulo': titulo, 'profesor': profesor, 'menu_tde': True}
    return render(request, 'incidenciatic.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misincidenciastic(request):
    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor

    curso_academico_actual = get_current_academic_year()



    lista_incidencias = IncidenciasTic.objects.filter(profesor__id=profesor.id, curso_academico=curso_academico_actual)
    lista_incidencias = sorted(lista_incidencias, key=lambda d: d.fecha, reverse=True)

    cursos_anteriores = get_previous_academic_years()
    lista_incidencias_anteriores = {}


    for curso in cursos_anteriores:
        inc_anteriores = IncidenciasTic.objects.filter(profesor__id=profesor.id, curso_academico=curso).order_by('fecha')

        if inc_anteriores:
            lista_incidencias_anteriores[curso] = inc_anteriores

    context = {'incidencias': lista_incidencias, 'incidencias_anteriores': lista_incidencias_anteriores, 'profesor': profesor, 'menu_tde': True}


    return render(request, 'misincidenciastic.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_tde, login_url='/')
def incidenciastic(request):
    curso_academico_actual = get_current_academic_year()

    lista_incidencias_pendientes = IncidenciasTic.objects.filter(resuelta=False, curso_academico=curso_academico_actual)
    lista_incidencias_resueltas = IncidenciasTic.objects.filter(resuelta=True, curso_academico=curso_academico_actual)

    cursos_anteriores = get_previous_academic_years()
    lista_incidencias_anteriores = {}

    for curso in cursos_anteriores:

        inc_anteriores = IncidenciasTic.objects.filter(curso_academico=curso).order_by(
            'fecha')

        # Solo añadir si hay incidencias pendientes o resueltas
        if inc_anteriores.exists():
            lista_incidencias_anteriores[curso] = inc_anteriores


    context = {'incidencias_pendientes': lista_incidencias_pendientes, 'incidencias_resueltas': lista_incidencias_resueltas, 'incidencias_anteriores': lista_incidencias_anteriores, 'menu_tde': True}


    return render(request, 'incidenciastic.html', context)

@csrf_exempt
def eliminar_incidencia(request):
    if request.method == 'POST':
        incidencia_id = request.POST.get('id')
        try:
            incidencia = IncidenciasTic.objects.get(id=incidencia_id)
            incidencia.delete()
            return JsonResponse({'success': True})
        except IncidenciasTic.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Incidencia no encontrada'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@csrf_exempt
@require_POST
def actualizar_incidencia(request):
    try:
        id = request.POST.get('id')
        solucion = request.POST.get('solucion')

        incidencia = IncidenciasTic.objects.get(id=id)
        incidencia.solucion = solucion
        incidencia.resuelta = True

        incidencia.save()

        # Mandamos correo al profesor/a
        destinatarios = []
        if incidencia.profesor.Email != "":
            destinatarios.append(incidencia.profesor.Email)

        template = get_template("correo_tde.html")
        contenido = template.render({'inc': incidencia})

        send_mail(
            'Incidencia TIC Resuelta',
            contenido,
            '41011038.jestudios.edu@juntadeandalucia.es',
            destinatarios,
            fail_silently=False,
        )

        return JsonResponse({'success': True})
    except IncidenciasTic.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Incidencia no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})