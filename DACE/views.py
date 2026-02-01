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

from collections import defaultdict
from datetime import datetime, time, timedelta
from sqlite3 import IntegrityError

from django.db.models import Q
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from centro.utils import get_current_academic_year
from centro.views import group_check_prof, group_check_je, group_check_je_or_dace
from .models import Actividades, ActividadAlumno, GastosActividad, Aprobaciones, EstadoActividad
from centro.models import Profesores, Cursos, Alumnos
from .forms import ActividadesForm, ActividadesCompletoForm, GestionEconomicaActividadForm, GastosActividadForm


@login_required
def crear_actividad(request):
    if request.method == 'POST':
        # Usamos el formulario completo si queremos que se gestione 'EnProgramacion' y otros campos
        form = ActividadesForm(request.POST)
        if form.is_valid():
            actividad = form.save(commit=False)
            actividad.Estado = get_object_or_404(EstadoActividad, nombre='Pendiente')

            try:
                actividad.save()
                form.save_m2m()  # Guardar relaciones ManyToMany
            except IntegrityError:
                # Aquí sería recomendable incluir un mensaje para el usuario
                print("Ya existe una actividad igual")

            return redirect('misactividades')
        else:
            print(form.errors)
    else:

        profe = getattr(request.user, 'profesor', None)
        initial = {'Responsable': profe} if profe else {}
        form = ActividadesForm(initial=initial)
    return render(request, 'crear_actividad.html', {'form': form, 'menu_DACE': True})


# @login_required
# def aprobar_actividad(request, actividad_id):
# actividad = get_object_or_404(Actividad, id=actividad_id)
# if request.method == 'POST':
#     form = AprobacionForm(request.POST)
#     if form.is_valid():
#         aprobacion = form.save(commit=False)
#         aprobacion.actividad = actividad
#         aprobacion.aprobado_por = request.user
#         aprobacion.save()
#         actividad.estado = 'Aprobada'
#         actividad.save()
#         return redirect('lista_actividades')
# else:
#     form = AprobacionForm()
# return render(request, 'gestion/aprobar_actividad.html', {'form': form, 'actividad': actividad})


# @login_required
# def calendario_actividades(request):
#     actividades = Actividades.objects.filter(estado='Aprobada')
#     return render(request, 'gestion/calendario_actividades.html', {'actividades': actividades})


@method_decorator(csrf_exempt, name='dispatch')
def aprobar_actividad(request, actividad_id):
    if request.method == 'POST':
        actividad = get_object_or_404(Actividades, id=actividad_id)
        aprobado_por = request.POST.get('aprobadoPor')
        fecha_aprobacion = request.POST.get('fechaAprobacion')

        if not aprobado_por or not fecha_aprobacion:
            return JsonResponse({'error': 'Faltan campos requeridos.'}, status=400)

        # Crear registro en el modelo Aprobaciones
        Aprobaciones.objects.create(
            Actividad=actividad,
            AprobadoPor=aprobado_por,
            Fecha=fecha_aprobacion
        )

        # Buscar estado "Aprobada" en la tabla EstadoActividad
        estado_aprobada = get_object_or_404(EstadoActividad, nombre="Aprobada")

        # Actualizar estado de la actividad
        actividad.Estado = estado_aprobada
        actividad.save()

        return JsonResponse({'message': 'Actividad aprobada exitosamente.'})
    return JsonResponse({'error': 'Método no permitido.'}, status=405)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misactividades(request):
    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor

    curso_academico_actual = get_current_academic_year()

    lista_actividades = Actividades.objects.filter(
        (Q(Responsable=profesor) | Q(Profesorado=profesor)),  # Responsable o participante
        curso_academico=curso_academico_actual
    ).distinct().order_by('-FechaInicio')

    context = {'actividades': lista_actividades, 'profesor': profesor, 'menu_DACE': True}

    return render(request, 'misactividades.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je_or_dace, login_url='/')
def actividadesdace(request):
    curso_academico_actual = get_current_academic_year()

    lista_actividades = Actividades.objects.filter(curso_academico=curso_academico_actual)
    lista_actividades = sorted(lista_actividades, key=lambda d: d.FechaInicio, reverse=True)

    context = {'actividades': lista_actividades, 'menu_DACE': True}

    return render(request, 'actividadesdace.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def editar_actividad(request, actividad_id):
    actividad = get_object_or_404(Actividades, id=actividad_id)

    if request.method == 'POST':
        form = ActividadesForm(request.POST, instance=actividad)
        if form.is_valid():
            try:
                actividad = form.save()
            except IntegrityError:
                print("Ya existe una actividad igual")

            return redirect('misactividades')  # Redirige al listado de actividades

    else:
        form = ActividadesForm(instance=actividad)
        # No es necesario asignar valores al widget attrs si usas DatePickerInput y ClockPickerInput correctamente configurados
        # Estos widgets deben manejar el formateo

    return render(request, 'editar_actividad.html', {'form': form, 'actividad': actividad})

@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def editar_actividad_participantes(request, actividad_id):
    actividad = get_object_or_404(Actividades, id=actividad_id)

    if request.method == 'POST':

        unidades_raw = request.POST.getlist('unidades_afectadas', '')
        unidades_ids = []
        for unidad in unidades_raw:
            if unidad:  # Verifica si el valor no está vacío
                unidades_ids.extend(unidad.split(','))  # Divide por comas y agrega los ids a la lista

        unidades_ids = [u for u in unidades_ids if u]
        print(f"Unidades procesadas: {unidades_ids}")
        actividad.UnidadesAfectadas.set(unidades_ids)

        # Procesar Alumnado Participante
        alumnos_ids_raw = request.POST.get('alumnado_participante', '')  # Obtén el valor como una cadena
        alumnos_ids = [u for u in alumnos_ids_raw.split(',') if u]  # Divide la cadena y filtra elementos vacíos

        actividad.Alumnado.set(alumnos_ids)

        profesorado_ids_raw = request.POST.get('profesorado_participante',
                                               '')  # Obtén el valor como cadena vacía si no hay nada
        profesorado_ids = [id for id in profesorado_ids_raw.split(',') if id]  # Filtra vacíos

        if profesorado_ids:  # Si hay IDs de profesorado, realizar el filtro
            actividad.Profesorado.set(Profesores.objects.filter(id__in=profesorado_ids))
        else:  # Si no hay profesorado, establecer como vacío
            actividad.Profesorado.clear()

        actividad.save()

        return redirect('misactividades')

    unidades = Cursos.objects.all()
    profesores = Profesores.objects.filter(Baja=False)
    return render(request, 'editar_actividad_participantes.html',
                  {'actividad': actividad, 'unidades': unidades, 'profesores': profesores})


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def editar_actividad_economica(request, actividad_id):
    actividad = get_object_or_404(Actividades, pk=actividad_id)
    alumnos = actividad.actividad_alumno.select_related('alumno', 'alumno__Unidad').order_by('alumno__Nombre')

    # Agrupar alumnos por unidad
    alumnos_por_unidad = defaultdict(list)
    alumnos_total = 0  # Inicializamos el contador de alumnos

    for alumno in alumnos:
        unidad = alumno.alumno.Unidad.Curso if alumno.alumno.Unidad else "Sin unidad"
        alumnos_por_unidad[unidad].append(alumno)
        alumnos_total += 1  # Incrementamos el contador

    # Formulario para los gastos
    GastosFormSet = modelformset_factory(GastosActividad, form=GastosActividadForm, extra=0, can_delete=False)
    formset = GastosFormSet(queryset=actividad.gastos.all())

    if request.method == 'POST':
        # Actualiza los costos
        form = GestionEconomicaActividadForm(request.POST, instance=actividad)
        formset = GastosFormSet(request.POST)

        if form.is_valid() and formset.is_valid():

            actividad = form.save()

            # Guardar los gastos
            gastos = formset.save(commit=False)
            for gasto in gastos:
                gasto.actividad = actividad
                gasto.save()

            # Actualiza el estado de pago de los alumnos
            for alumno in alumnos:
                pagado = request.POST.get(f"pagado_{alumno.id}", "off") == "on"
                compe = request.POST.get(f"compe_{alumno.id}", "off") == "on"
                actividad_alumno = ActividadAlumno.objects.get(actividad=actividad, alumno=alumno.alumno)
                actividad_alumno.ha_pagado = pagado
                actividad_alumno.compe = compe
                actividad_alumno.save()

            return redirect('actividadesdace')

        else:
            # Depuración de errores
            if not form.is_valid():
                print("Errores en el formulario principal:")
                print(form.errors)
            if not formset.is_valid():
                print("Errores en el formset:")
                for i, form_errors in enumerate(formset.errors):
                    print(f"Errores en el formulario {i + 1}: {form_errors}")
                print("Errores globales en el formset:")
                print(formset.non_form_errors())



    else:
        form = GestionEconomicaActividadForm(instance=actividad)

    return render(request, 'editar_actividad_economica.html', {
        'actividad': actividad,
        'alumnos_por_unidad': dict(alumnos_por_unidad),
        'form': form,
        'formset': formset,
        'alumnos_total': alumnos_total
    })


@login_required(login_url='/')
def get_alumnos_unidad(request, unidad_id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        alumnos = Alumnos.objects.filter(Unidad_id=unidad_id).values('id', 'Nombre')
        return JsonResponse({'alumnos': list(alumnos)})

    return JsonResponse({'error': 'Esta no es una solicitud AJAX.'})


def get_alumnos_participantes_unidad(request, unidad_id, actividad_id):
    try:
        actividad = Actividades.objects.get(id=actividad_id)
        unidad = Cursos.objects.get(id=unidad_id)

        # Obtener el alumnado participante de la actividad y perteneciente a la unidad
        alumnos = actividad.Alumnado.filter(Unidad=unidad)
        data = [{'id': alumno.id, 'Nombre': alumno.Nombre} for alumno in alumnos]
        return JsonResponse({'alumnos': data}, status=200)
    except Actividades.DoesNotExist:
        return JsonResponse({'error': 'Actividad no encontrada'}, status=404)
    except Cursos.DoesNotExist:
        return JsonResponse({'error': 'Unidad no encontrada'}, status=404)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def detalles_actividad(request, actividad_id):
    actividad = get_object_or_404(Actividades, pk=actividad_id)
    alumnos = actividad.actividad_alumno.select_related('alumno', 'alumno__Unidad').order_by('alumno__Nombre')

    # Agrupar alumnos por unidad
    alumnos_por_unidad = defaultdict(list)
    alumnos_total = 0  # Inicializamos el contador de alumnos

    for alumno in alumnos:
        unidad = alumno.alumno.Unidad.Curso if alumno.alumno.Unidad else "Sin unidad"
        alumnos_por_unidad[unidad].append(alumno)
        alumnos_total += 1  # Incrementamos el contador

    gastos = actividad.gastos.all()

    return render(request, 'detalles_actividad.html', {
        'actividad': actividad,
        'alumnos_por_unidad': dict(alumnos_por_unidad),
        'alumnos_total': alumnos_total,
        'gastos': gastos
    })


@csrf_exempt
def actividadesdace_json(request):
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    start_date = datetime.fromisoformat(start_str)
    end_date = datetime.fromisoformat(end_str)

    actividades = Actividades.objects.filter(
        Estado__nombre="Aprobada",
        FechaInicio__lte=end_date,
        FechaFin__gte=start_date
    )

    eventos = []
    for actividad in actividades:
        unidades = [str(u) for u in actividad.UnidadesAfectadas.all()]  # listado legible

        if actividad.HoraSalida and actividad.HoraLlegada:
            start_dt = datetime.combine(actividad.FechaInicio, actividad.HoraSalida)
            end_dt = datetime.combine(actividad.FechaFin, actividad.HoraLlegada)
            all_day = False
        else:
            start_dt = actividad.FechaInicio
            end_dt = actividad.FechaFin + timedelta(days=1)  # FullCalendar requiere +1 para allDay
            all_day = True

        eventos.append({
            'title': actividad.Titulo,
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'allDay': all_day,
            'className': 'bg-success-subtle text-success border-start border-3 border-success',
            'extendedProps': {
                'descripcion': actividad.Descripcion or '',
                'responsable': str(actividad.Responsable),
                'unidades': unidades,
                'id' : actividad.id,
            }
        })

    return JsonResponse(eventos, safe=False)


def actividades_calendario(request):
    return render(request, "actividadescal.html")


@method_decorator(csrf_exempt, name='dispatch')
def desaprobar_actividad(request, actividad_id):
    if request.method == 'POST':
        actividad = get_object_or_404(Actividades, id=actividad_id)

        # Eliminar aprobaciones relacionadas
        actividad.aprobaciones.all().delete()

        # Restaurar estado Pendiente
        estado_pendiente = get_object_or_404(EstadoActividad, nombre="Pendiente")
        actividad.Estado = estado_pendiente
        actividad.save()

        return JsonResponse({'message': 'Actividad desaprobada correctamente.'})
    return JsonResponse({'error': 'Método no permitido.'}, status=405)


@method_decorator(csrf_exempt, name='dispatch')
def borrar_actividad(request, actividad_id):
    if request.method == 'POST':
        actividad = get_object_or_404(Actividades, id=actividad_id)

        # Opcional: verificar permisos antes de borrar

        # Borrar actividad y relaciones en cascada
        actividad.delete()

        return JsonResponse({'message': 'Actividad borrada correctamente.'})
    return JsonResponse({'error': 'Método no permitido.'}, status=405)
