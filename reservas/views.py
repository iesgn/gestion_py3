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

import json
from datetime import timedelta, datetime, date
from sqlite3 import IntegrityError

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from centro.utils import get_current_academic_year
from centro.views import group_check_prof, group_check_je, group_check_tde
from horarios.models import ItemHorario
from reservas.forms import ReservaForm, ReservaProfeForm
from reservas.models import Reservas, Reservables


# Create your views here.

@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def crear_reserva(request):
    profesor = request.user.profesor

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():

            reserva = form.save(commit=False)
            reserva.Profesor = profesor  # Asignar el profesor desde el contexto

            periodicidad = form.cleaned_data['periodicidad']
            num_semanas = form.cleaned_data.get('num_semanas', 1)
            fecha_inicial = form.cleaned_data['Fecha']
            tramos_seleccionados = request.POST.get('tramos_seleccionados', '[]')


            # Asegurarse de que tramos_seleccionados sea una lista
            if tramos_seleccionados:
                tramos_seleccionados = json.loads(tramos_seleccionados)
            else:
                tramos_seleccionados = []

            errores = []

            for i in range(int(num_semanas)):
                nueva_fecha = fecha_inicial + timedelta(weeks=i)
                for tramo in tramos_seleccionados:
                    # Verificar si ya existe una reserva
                    if Reservas.objects.filter(Fecha=nueva_fecha, Hora=tramo, Reservable=reserva.Reservable).exists():
                        errores.append(f'Ya existe una reserva para el {nueva_fecha} en la {tramo}ª hora.')
                    else:
                        Reservas.objects.get_or_create(
                            Profesor=reserva.Profesor,
                            Fecha=nueva_fecha,
                            Hora=tramo,
                            Reservable=reserva.Reservable
                        )

            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'nuevareserva.html', {'form': form, 'profesor': profesor, 'menu_reservas': True})



            return redirect('misreservas')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
            return render(request, 'nuevareserva.html', {'form': form, 'profesor': profesor, 'menu_reservas': True})
    else:
        form = ReservaForm()

    return render(request, 'nuevareserva.html', {'form': form, 'profesor': profesor, 'menu_reservas': True})



@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def crear_reserva_profe(request):


    if request.method == 'POST':
        form = ReservaProfeForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)

            periodicidad = form.cleaned_data['periodicidad']
            num_semanas = form.cleaned_data.get('num_semanas', 1)
            fecha_inicial = form.cleaned_data['Fecha']
            tramos_seleccionados = request.POST.get('tramos_seleccionados', '[]')


            # Asegurarse de que tramos_seleccionados sea una lista
            if tramos_seleccionados:
                tramos_seleccionados = json.loads(tramos_seleccionados)
            else:
                tramos_seleccionados = []

            reservas = []
            errores = []

            for i in range(int(num_semanas)):
                nueva_fecha = fecha_inicial + timedelta(weeks=i)
                for tramo in tramos_seleccionados:
                    # Verificar si ya existe una reserva
                    if Reservas.objects.filter(Fecha=nueva_fecha, Hora=tramo, Reservable=reserva.Reservable).exists():
                        errores.append(f'Ya existe una reserva para el {nueva_fecha} en la {tramo}ª hora.')
                    else:
                        nueva_reserva = Reservas(
                            Profesor=reserva.Profesor,
                            Fecha=nueva_fecha,
                            Hora=tramo,
                            Reservable=reserva.Reservable
                        )
                        reservas.append(nueva_reserva)

            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'nuevareservaprofe.html', {'form': form, 'menu_reservas': True})

            Reservas.objects.bulk_create(reservas)
            return redirect('verreservas')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
            return render(request, 'nuevareservaprofe.html', {'form': form, 'menu_reservas': True})
    else:
        form = ReservaProfeForm()

    return render(request, 'nuevareservaprofe.html', {'form': form, 'menu_reservas': True})


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misreservas(request):
    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor

    lista_reservas = Reservas.objects.filter(Profesor__id=profesor.id)
    lista_reservas = sorted(lista_reservas, key=lambda d: d.Fecha, reverse=True)

    context = {'reservas': lista_reservas, 'profesor': profesor, 'menu_reservas': True}

    return render(request, 'misreservas.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_tde, login_url='/')
def reservas(request):
    curso_academico_actual = get_current_academic_year()
    hoy = date.today()

    # Reservas activas: hoy o futuras
    reservas_activas_qs = Reservas.objects.filter(
        curso_academico=curso_academico_actual,
        Fecha__gte=hoy
    ).order_by('Fecha')

    # Reservas pasadas: fecha < hoy (si quieres, limita a las últimas N)
    reservas_pasadas_qs = Reservas.objects.filter(
        curso_academico=curso_academico_actual,
        Fecha__lt=hoy
    ).order_by('-Fecha')[:1000]  # por ejemplo, últimas 1000

    def construir_info(lista_reservas):
        info = []
        for reserva in lista_reservas.select_related('Profesor', 'Reservable__TiposReserva'):
            item_horario = ItemHorario.objects.filter(
                profesor=reserva.Profesor,
                dia=reserva.Fecha.weekday() + 1,
                tramo=int(reserva.Hora)
            ).select_related('unidad', 'aula').first()

            info.append({
                'r': reserva,
                'curso': item_horario.unidad if item_horario else None,
                'aula': item_horario.aula if item_horario else None,
            })
        return info

    reservas_activas = construir_info(reservas_activas_qs)
    reservas_pasadas = construir_info(reservas_pasadas_qs)

    context = {
        'reservas_activas': reservas_activas,
        'reservas_pasadas': reservas_pasadas,
        'menu_reservas': True,
    }
    return render(request, 'reservas.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_tde, login_url='/')
def reservascal(request):


    lista_reservas = Reservas.objects.all()
    lista_reservas = sorted(lista_reservas, key=lambda d: d.Fecha, reverse=True)

    context = {'reservas': lista_reservas, 'menu_reservas': True}

    return render(request, 'reservascal.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def filter_reservables(request):
    tipo_id = request.GET.get('tipo_id')
    reservables = Reservables.objects.filter(TiposReserva_id=tipo_id).values('id', 'Nombre')
    return JsonResponse(list(reservables), safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def verificar_disponibilidad(request):
    reservable_id = request.GET.get('reservable_id')
    fecha = request.GET.get('fecha')

    # Validar que ambos parámetros estén presentes
    if reservable_id and fecha:
        try:
            # Convertir la fecha al formato adecuado
            fecha = datetime.strptime(fecha, '%d/%m/%Y').date()

            # Verificar la disponibilidad de cada tramo horario
            disponibilidad = {}
            for hora in range(1, 8):
                reserva = Reservas.objects.filter(Reservable_id=reservable_id, Fecha=fecha, Hora=str(hora)).first()
                if reserva:
                    disponibilidad[f'hora{hora}'] = {
                        'existe_reserva': True,
                        'profesor_id': reserva.Profesor.id,
                        'profesor_nombre': reserva.Profesor.Apellidos + ", "+reserva.Profesor.Nombre
                    }
                else:
                    disponibilidad[f'hora{hora}'] = {
                        'existe_reserva': False,
                        'profesor_id': None,
                        'profesor_nombre': None
                    }

            return JsonResponse(disponibilidad)
        except ValueError:
            # Error en la conversión de la fecha
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    # Si faltan parámetros, devolver un error
    return JsonResponse({'error': 'Faltan parámetros'}, status=400)


@csrf_exempt
def eliminar_reserva(request):
    if request.method == 'POST':
        reserva_id = request.POST.get('id')
        try:
            reserva = Reservas.objects.get(id=reserva_id)
            reserva.delete()
            return JsonResponse({'success': True})
        except Reservas.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Reserva no encontrada'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@csrf_exempt
def reservas_json(request):
    # Obtener los parámetros start y end de la URL
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    # Convertir las cadenas de fecha a objetos datetime
    start_date = datetime.fromisoformat(start_str)
    end_date = datetime.fromisoformat(end_str)

    # Obtener las reservas dentro del rango de fechas
    reservas = Reservas.objects.filter(Fecha__range=(start_date, end_date))

    # Diccionario para las horas
    horas = {
        1: ('08:15', '09:15'),
        2: ('09:15', '10:15'),
        3: ('10:15', '11:15'),
        4: ('11:15', '11:45'),
        5: ('11:45', '12:45'),
        6: ('12:45', '13:45'),
        7: ('13:45', '14:45'),
    }

    # Formatear las reservas en el formato esperado por FullCalendar
    eventos = []
    for reserva in reservas:
        hora_id = int(reserva.Hora)  # Convertir Hora a entero
        start_time, end_time = horas[hora_id]
        start_datetime = f'{reserva.Fecha}T{start_time}:00'
        end_datetime = f'{reserva.Fecha}T{end_time}:00'

        # Asignar color según el tipo de reservable

        if str(reserva.Reservable.TiposReserva) == 'Espacio':
            classname = 'bg-primary-subtle text-primary border-start border-3 border-primary'  # Verde para Espacio
        else:
            classname = 'bg-info-subtle text-info border-start border-3 border-info'  # Azul para Recurso


        eventos.append({
            'title': f'{reserva.Profesor} - {reserva.Reservable}',
            'profesor': f'{reserva.Profesor}',
            'reservable' : f'{reserva.Reservable}',
            'start': start_datetime,
            'end': end_datetime,
            'className': classname,
        })

    return JsonResponse(eventos, safe=False)