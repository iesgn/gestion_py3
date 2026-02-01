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

import calendar
import json
import locale
from collections import defaultdict, OrderedDict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.db.models import Count, Q
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime

from centro.models import Profesores, Cursos, Aulas, CursoAcademico
from centro.utils import get_current_academic_year
from centro.views import group_check_je, group_check_prof, group_check_prof_or_guardia, group_check_je_or_conserjes
from convivencia.forms import FechasForm
from guardias.forms import ItemGuardiaForm
from guardias.models import ItemGuardia, TiempoGuardia
from horarios.models import ItemHorario
from datetime import datetime, date

from itertools import groupby
from operator import itemgetter



# Create your views here.

# Diccionario para traducir días de la semana
dias_semana_es = {
    'Monday': 'LUNES',
    'Tuesday': 'MARTES',
    'Wednesday': 'MIÉRCOLES',
    'Thursday': 'JUEVES',
    'Friday': 'VIERNES',
    'Saturday': 'SÁBADO',
    'Sunday': 'DOMINGO'
}

meses_es = {
    'January': 'enero',
    'February': 'febrero',
    'March': 'marzo',
    'April': 'abril',
    'May': 'mayo',
    'June': 'junio',
    'July': 'julio',
    'August': 'agosto',
    'September': 'septiembre',
    'October': 'octubre',
    'November': 'noviembre',
    'December': 'diciembre'
}

# Diccionario de correspondencia de tramos
TRAMOS_NOMBRES = {
    1: "1ª hora",
    2: "2ª hora",
    3: "3ª hora",
    4: "Recreo",
    5: "4ª hora",
    6: "5ª hora",
    7: "6ª hora",
}


# Formatear la fecha
def formatear_fecha(fecha):
    dia_semana = dias_semana_es[fecha.strftime('%A')]
    mes = meses_es[fecha.strftime('%B')]
    return f"{dia_semana}, {fecha.strftime('%d')} de {mes} de {fecha.strftime('%Y')}".capitalize()


def itemguardia_to_dict(item):
    # Obtener los nombres de los profesores de guardia
    profesores_guardia = [prof.nombre_completo for prof in item.ProfesoresGuardia.all()]

    return {
        'tramo_num': item.Tramo,
        'tramo': TRAMOS_NOMBRES.get(item.Tramo, f'Tramo {item.Tramo}'),
        'materia': item.Materia,
        'unidad': item.Unidad.Curso if item.Unidad else 'Sin unidad',  # Aseguramos que no sea None
        'aula': item.Aula.Aula if item.Aula else 'Sin aula',  # Aseguramos que no sea None
        'tarea': item.Tarea if item.Tarea else 'Sin tarea',  # Aseguramos que no sea None
        'profesores_guardia': profesores_guardia,
        'profesor_notifica': str(item.ProfesorNotifica),
        'profesor_confirma': str(item.ProfesorConfirma)
    }


@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia, login_url='/')
def parteguardias(request):
    context = {
        'menu_guardias': True
    }
    return render(request, 'parteguardias.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misausencias(request):
    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor
    curso_academico_actual = get_current_academic_year()

    # Buscar los ItemGuardia cuyo ProfesorAusente es el profesor actual
    ausencias = ItemGuardia.objects.filter(ProfesorAusente=profesor, curso_academico=curso_academico_actual).order_by(
        '-Fecha')

    # Diccionario ordenado para agrupar por fecha
    ausencias_agrupadas = OrderedDict()

    # Fecha actual
    hoy = datetime.now().date()

    # Agrupar por fecha
    for ausencia in ausencias:
        fecha = ausencia.Fecha
        if fecha not in ausencias_agrupadas:
            ausencias_agrupadas[fecha] = []
        ausencias_agrupadas[fecha].append(ausencia)

    # Formatear los datos para la tabla
    datos_agrupados = []
    for fecha, items in ausencias_agrupadas.items():
        dia_semana = dias_semana_es[fecha.strftime('%A')]  # Traducir día al español
        # dia_semana = fecha.strftime('%A').upper()
        es_futuro = fecha > hoy  # Comprobar si la fecha es futura
        datos_agrupados.append({
            'fecha': fecha.strftime('%d/%m/%Y'),  # Fecha en formato ISO para facilitar la consulta AJAX
            'diasemana': dia_semana,
            'tramos_ausente': len(items),  # Número de tramos ausente
            'es_futuro': es_futuro  # Añadimos la información de si es futuro o no
        })

    context = {
        'profesor': profesor,
        'datos_agrupados': datos_agrupados,  # Solo enviamos los datos básicos
        'menu_guardias': True
    }

    return render(request, 'misausencias.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia, login_url='/')
def horario_profesor_ajax(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Obtener los parámetros de la solicitud
        fecha_str = request.GET.get('fecha')
        profesor_id = request.GET.get('profesor_id')
        curso_academico_actual = get_current_academic_year()

        # Convertir la fecha a un objeto datetime
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')

        # Obtener el día de la semana (1=Lunes, 2=Martes,...)
        dia_semana = fecha.isoweekday()

        profesor = Profesores.objects.get(id=profesor_id)

        # Filtrar los items del horario según el profesor y el día de la semana
        items_horario = ItemHorario.objects.filter(profesor_id=profesor_id, dia=dia_semana,
                                                   curso_academico=curso_academico_actual).order_by('tramo')

        # Agrupar por tramo, materia y aula, y concatenar las unidades
        horario_agrupado = defaultdict(lambda: {'unidades': []})

        for item in items_horario:
            # Usamos una clave única que agrupa por tramo, materia y aula
            clave = (item.tramo, item.materia, item.aula.AulaHorarios)

            # Añadimos la unidad a la lista de unidades de esa clave
            horario_agrupado[clave]['unidades'].append(item.unidad)

            # Si no se ha agregado previamente, añadimos otros datos estáticos
            if 'materia' not in horario_agrupado[clave]:
                horario_agrupado[clave]['materia'] = item.materia
                horario_agrupado[clave]['aula'] = item.aula.AulaHorarios

            # Comprobamos si ya existe un ItemGuardia para el profesor, la fecha y el tramo
            guardia_exists = ItemGuardia.objects.filter(ProfesorAusente_id=profesor_id, Fecha=fecha,
                                                        Tramo=item.tramo).exists()
            horario_agrupado[clave]['guardia_exists'] = guardia_exists
            horario_agrupado[clave]['tramo'] = TRAMOS_NOMBRES.get(item.tramo, f'Tramo {item.tramo}')
            horario_agrupado[clave]['tramo_num'] = item.tramo

        # Convertimos el diccionario agrupado a una lista para la respuesta
        items_data = []
        for clave, datos in horario_agrupado.items():
            unidades_concatenadas = ', '.join(
                [str(unidad) for unidad in datos['unidades']])  # Convertir las unidades a string y unirlas
            items_data.append({
                'tramo_num': datos['tramo_num'],
                'tramo': datos['tramo'],
                'materia': datos['materia'],
                'unidad': unidades_concatenadas,
                'aula': datos['aula'],
                'guardia_exists': datos['guardia_exists']
            })

        # locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        fecha_formateada = formatear_fecha(fecha)
        # fecha_formateada = fecha.strftime("%A, %d de %B, %Y").capitalize()

        # Renderizar una plantilla parcial con los items del horario
        return render(request, 'partials/horario_items.html', {'items_horario': items_data, 'fecha': fecha_formateada})

    return JsonResponse({'error': 'Esta no es una solicitud AJAX.'})


@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia, login_url='/')
def guardar_guardias_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Obtener los datos del formulario
        fecha_str = request.POST.get('fecha')
        profesor_ausente_id = request.POST.get('profesor_ausente')
        seleccionados = json.loads(request.POST.get('seleccionados'))
        curso_academico_actual = get_current_academic_year()

        # Convertir la fecha a un objeto datetime
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')

        # Obtener el profesor ausente
        profesor_ausente = Profesores.objects.get(id=profesor_ausente_id)

        # Crear los objetos ItemGuardia
        for seleccionado in seleccionados:

            # Aquí obtienes los valores de cada fila
            tramo = seleccionado['tramo']
            materia = seleccionado['materia']
            unidad_nombre = seleccionado['unidad']
            aula_nombre = seleccionado['aula']
            tarea = seleccionado['tarea']

            # Extraer solo la primera unidad si hay varias
            unidad_nombre_principal = unidad_nombre.split(',')[0]  # Obtener la primera unidad

            # Buscar la unidad y el aula por nombre
            try:
                unidad = Cursos.objects.get(Curso=unidad_nombre_principal)
            except Cursos.DoesNotExist:
                unidad = None

            try:
                aula = Aulas.objects.get(AulaHorarios=aula_nombre)
            except Aulas.DoesNotExist:
                aula = None

            # Crear el nuevo ItemGuardia
            ItemGuardia.objects.get_or_create(
                Unidad=unidad,
                ProfesorAusente=profesor_ausente,
                Aula=aula,
                Tarea=tarea,
                Materia=materia,
                Fecha=fecha,
                Tramo=tramo,
                ProfesorNotifica=request.user.profesor,
                curso_academico=curso_academico_actual,
            )

        # Devolver una respuesta de éxito
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Método no permitido o no es una solicitud AJAX.'}, status=400)


def obtener_itemguardia_por_fecha(request):
    fecha_str = request.GET.get('fecha')  # Recibimos la fecha desde el AJAX

    if not hasattr(request.user, 'profesor'):
        return JsonResponse({'error': 'No tiene un perfil de profesor asociado.'}, status=403)

    profesor = request.user.profesor
    curso_academico_actual = get_current_academic_year()

    # Convertir la fecha de cadena a objeto datetime
    try:
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')  # Convertir el formato de fecha
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha incorrecto.'}, status=400)

    # Filtramos los ItemGuardia por fecha y profesor
    itemguardias = ItemGuardia.objects.filter(ProfesorAusente=profesor, Fecha=fecha,
                                              curso_academico=curso_academico_actual)

    # Convertir los itemguardias a un diccionario
    itemguardia_list = [itemguardia_to_dict(item) for item in itemguardias]

    return JsonResponse(itemguardia_list, safe=False)


def obtener_itemguardia_por_fecha_y_profe(request):
    fecha_str = request.GET.get('fecha')  # Recibimos la fecha desde el AJAX
    profe = request.GET.get('profesor')
    curso_academico_actual = get_current_academic_year()

    # Convertir la fecha de cadena a objeto datetime
    try:
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')  # Convertir el formato de fecha
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha incorrecto.'}, status=400)

    # Filtramos los ItemGuardia por fecha y profesor
    itemguardias = ItemGuardia.objects.filter(ProfesorAusente_id=profe, Fecha=fecha,
                                              curso_academico=curso_academico_actual)

    # Convertir los itemguardias a un diccionario
    itemguardia_list = [itemguardia_to_dict(item) for item in itemguardias]

    return JsonResponse(itemguardia_list, safe=False)


def parteguardias_ajax(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        fecha_str = request.GET.get('fecha')
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
        curso_academico_actual = get_current_academic_year()

        # Filtrar los ItemGuardia según la fecha
        item_guardias = ItemGuardia.objects.filter(Fecha=fecha, curso_academico=curso_academico_actual)

        # Filtrar los ItemHorario para encontrar profesores de guardia
        item_horarios = ItemHorario.objects.filter(dia=fecha.weekday() + 1, curso_academico=curso_academico_actual)

        # Obtener el día de la semana para TiempoGuardia (Lunes: 1, Martes: 2, etc.)
        dia_semana = fecha.weekday() + 1

        # Preparar la lista de profesores con su tiempo de guardia por tramo
        profesores_guardia_info = {}

        for tramo in range(1, 8):  # Tramos de 1 a 7 (1ª Hora a 6ª Hora más Recreo)
            # Obtener todos los IDs de los profesores asignados en el tramo y materia 'GUARDIAS'
            profesor_ids = item_horarios.filter(
                Q(tramo=tramo) & Q(materia__in=["GUARDIAS", "GUARDIAS (PG1)", "GUARDIAS (PG2)", "GUARDIAS (PG3)", "GUARDIAS (PG4)", "GUARDIA CONVIVENCIA", "GUARDIA HORIZONTE", "GUARDIA ACE"]) & Q(
                    profesor__Baja=False)
            ).values_list('profesor', flat=True).distinct()

            # Para cada profesor, obtener el tiempo de guardia
            profesores_info = []
            for profesor in Profesores.objects.filter(id__in=profesor_ids):
                # Sumar el tiempo asignado en ese tramo y día para este profesor
                tiempos_guardia = TiempoGuardia.objects.filter(profesor=profesor, tramo=tramo, dia_semana=dia_semana, curso_academico=curso_academico_actual)
                tiempo_total = sum(tg.tiempo_asignado for tg in tiempos_guardia)  # Acumular el tiempo total

                # Determinar si el profesor tiene "GUARDIA CONVIVENCIA"
                # materia_guardia = item_horarios.filter(tramo=tramo, profesor=profesor).first().materia
                materias_guardia = item_horarios.filter(tramo=tramo, profesor=profesor).values_list('materia',
                                                                                                    flat=True).distinct()

                # Convertir tiempo a horas y minutos
                if tiempo_total >= 60:
                    horas = tiempo_total // 60
                    minutos = tiempo_total % 60
                    if minutos > 0:
                        tiempo_str = f"{horas} h {minutos} min"
                    else:
                        tiempo_str = f"{horas} h"
                else:
                    tiempo_str = f"{tiempo_total} min"

                # Calcular la puntuación multiplicando el tiempo cubierto por la dificultad de los cursos
                puntuacion = 0
                for tiempo in tiempos_guardia:
                    item_guardia = tiempo.item_guardia  # Relacionar con ItemGuardia
                    if item_guardia:
                        curso = item_guardia.Unidad  # Obtener el curso
                        dificultad = curso.Dificultad  # Obtener la dificultad del curso
                        if dificultad:
                            puntuacion += tiempo.tiempo_asignado * dificultad  # Calcular la puntuación
                        else:
                            puntuacion = 0

                profesores_info.append({
                    'id': profesor.id,
                    'nombre': f"{profesor.Apellidos}, {profesor.Nombre}",
                    'materia': profesor.Departamento,  # Asegúrate de que el modelo 'Profesor' tenga el campo 'materia'
                    'tiempo': tiempo_str,
                    'tiempo_minutos': tiempo_total,
                    'puntuacion': puntuacion,  # Guardar la puntuación calculada
                    'es_guardia_convivencia': (
                            "GUARDIA CONVIVENCIA" in materias_guardia or
                            "GUARDIA HORIZONTE" in materias_guardia
                    ),
                    'es_guardia_DACE': ("GUARDIA ACE" in materias_guardia),
                    'es_guardia_PG1': ("GUARDIAS (PG1)" in materias_guardia),
                    'es_guardia_PG2': ("GUARDIAS (PG2)" in materias_guardia),
                    'es_guardia_PG3': ("GUARDIAS (PG3)" in materias_guardia),
                    'es_guardia_PG4': ("GUARDIAS (PG4)" in materias_guardia),
                })

            # Ordenar la lista primero por tiempo y luego por porcentaje
            profesores_info.sort(
                key=lambda x: (x['es_guardia_DACE'], x['es_guardia_convivencia'], x['tiempo_minutos'], x['puntuacion']))

            profesores_guardia_info[tramo] = profesores_info

        # Asegurarse de que siempre exista una lista, aunque esté vacía
        for tramo in range(1, 8):
            if tramo not in profesores_guardia_info:
                profesores_guardia_info[tramo] = []

        for tramo, profesores in profesores_guardia_info.items():

            # Calcular el porcentaje en función de la puntuación más alta por tramo
            max_puntuacion = max([prof['puntuacion'] for prof in profesores] or [
                1])  # Evitar dividir por 0 en caso de que no haya puntuaciones

            for profesor in profesores:
                profesor['porcentaje'] = round(
                    (profesor['puntuacion'] / max_puntuacion) * 100) if max_puntuacion > 0 else 0

        # Preparar las tablas para cada tramo horario
        tablas = {}

        item_guardias_por_tramo = defaultdict(list)

        # Iterar sobre cada tramo de 1 a 7
        for tramo in range(1, 8):
            # Filtrar los ItemGuardia por el tramo actual
            item_guardias_tramo = item_guardias.filter(Tramo=tramo)

            # Procesar cada guardia en el tramo actual
            for guardia in item_guardias_tramo:
                guardia.profesor_tiempos = []

                # Iterar sobre cada profesor en ProfesoresGuardia para esta guardia
                for profesor in guardia.ProfesoresGuardia.all():
                    # Obtener el tiempo asignado para el profesor específico en esta guardia
                    tiempo_guardia = TiempoGuardia.objects.filter(
                        profesor=profesor,
                        item_guardia=guardia
                    ).first()

                    # Agregar al contexto el profesor y su tiempo asignado
                    guardia.profesor_tiempos.append({
                        'profesor': profesor,
                        'tiempo_asignado': tiempo_guardia.tiempo_asignado if tiempo_guardia else 0
                    })

                # Agregar la guardia con la información de tiempos al diccionario por tramo
                item_guardias_por_tramo[tramo].append(guardia)

        # Pasar la lista de profesores a las tablas con los nombres correctos de las tablas
        tablas['tabla_1h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 1,
            'item_guardias': item_guardias_por_tramo[1],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=1)),
            'profesores_guardia': profesores_guardia_info[1],
            'profesor_confirma': request.user.profesor,
        })
        tablas['tabla_2h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 2,
            'item_guardias': item_guardias_por_tramo[2],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=2)),
            'profesores_guardia': profesores_guardia_info[2],
            'profesor_confirma': request.user.profesor,
        })
        tablas['tabla_3h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 3,
            'item_guardias': item_guardias_por_tramo[3],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=3)),
            'profesores_guardia': profesores_guardia_info[3],
            'profesor_confirma': request.user.profesor,
        })
        tablas['tabla_rec'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 4,
            'item_guardias': item_guardias_por_tramo[4],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=4)),
            'profesores_guardia': profesores_guardia_info[4],
            'profesor_confirma': request.user.profesor,
        })

        tablas['tabla_4h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 5,
            'item_guardias': item_guardias_por_tramo[5],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=5)),
            'profesores_guardia': profesores_guardia_info[5],
            'profesor_confirma': request.user.profesor,
        })
        tablas['tabla_5h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 6,
            'item_guardias': item_guardias_por_tramo[6],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=6)),
            'profesores_guardia': profesores_guardia_info[6],
            'profesor_confirma': request.user.profesor,
        })
        tablas['tabla_6h'] = render_to_string('partials/tabla_guardias.html', {
            'tramo': 7,
            'item_guardias': item_guardias_por_tramo[7],
            'item_guardias_data': serializar_item_guardias(item_guardias.filter(Tramo=7)),
            'profesores_guardia': profesores_guardia_info[7],
            'profesor_confirma': request.user.profesor,
        })

        # Renderizar la plantilla parcial para los iboxes de profesores de guardia
        ibox_guardias = render_to_string('partials/ibox_guardias.html', {
            'profesores_guardia_info': profesores_guardia_info
        })

        # Devolver la respuesta en formato JSON con tablas e iboxes
        return JsonResponse({
            'tablas': tablas,
            'ibox_guardias': ibox_guardias
        })

    return JsonResponse({'error': 'Esta no es una solicitud AJAX.'})


# Función para serializar item_guardias a diccionarios
def serializar_item_guardias(item_guardias):
    item_guardias_data = []
    for guardia in item_guardias:
        # Convertimos cada guardia en un diccionario
        guardia_data = model_to_dict(guardia,
                                     fields=['id', 'ProfesorAusente', 'Materia', 'Unidad', 'Aula', 'ProfesorConfirma'])

        # Reemplazamos None por 'null' en los campos que lo necesiten, utilizando una comprensión de diccionario
        guardia_data = {key: (value if value is not None else 'null') for key, value in guardia_data.items()}

        # Agregamos datos de ProfesoresGuardia con su tiempo asignado
        profesores_guardia_data = []
        for profesor in guardia.ProfesoresGuardia.all():
            tiempo_guardia = TiempoGuardia.objects.filter(
                profesor=profesor,
                item_guardia=guardia
            ).first()  # Usamos .first() para obtener solo un tiempo

            # Añadimos los datos del profesor y su tiempo asignado
            profesor_data = {
                'id': profesor.id,
                'nombre': f"{profesor.Apellidos}, {profesor.Nombre}",
                'tiempo_asignado': tiempo_guardia.tiempo_asignado if tiempo_guardia else 0
                # Asignar 0 si no hay tiempo registrado
            }
            profesores_guardia_data.append(profesor_data)

        # Añadimos la lista completa de profesores con sus tiempos a guardia_data
        guardia_data['ProfesoresGuardia'] = profesores_guardia_data

        # Añadimos la guardia serializada a la lista principal
        item_guardias_data.append(guardia_data)

    return item_guardias_data


'''
def confirmar_guardia_ajax(request):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Obtener los datos enviados mediante POST
        item_guardia_id = request.POST.get('item_guardia_id')
        profesores_guardia_ids = request.POST.getlist('profesores_guardia_ids[]')
        profesor_confirma_id = request.POST.get('profesor_confirma_id')

        try:
            # Obtener el ItemGuardia que se va a actualizar
            item_guardia = ItemGuardia.objects.get(id=item_guardia_id)

            # Obtener los objetos de los profesores seleccionados
            profesores_guardia = Profesores.objects.filter(id__in=profesores_guardia_ids)

            # Actualizar los campos correspondientes en ItemGuardia
            item_guardia.ProfesoresGuardia.set(profesores_guardia)  # Añadir los profesores seleccionados
            item_guardia.ProfesorConfirma_id = profesor_confirma_id  # Asignar el profesor que confirmó
            item_guardia.save()

            # Repartir el tiempo entre los profesores seleccionados
            num_profesores = len(profesores_guardia_ids)
            tiempo_por_profesor = 60 // num_profesores if num_profesores else 0

            for profesor_id in profesores_guardia_ids:
                profesor = Profesores.objects.get(id=profesor_id)
                TiempoGuardia.objects.get_or_create(
                    profesor=profesor,
                    dia_semana=item_guardia.Fecha.weekday() + 1,  # 1:Lunes, 2:Martes, etc.
                    tramo=item_guardia.Tramo,
                    tiempo_asignado=tiempo_por_profesor,
                    item_guardia=item_guardia
                )

            return JsonResponse({'success': True})

        except ItemGuardia.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ItemGuardia no encontrado'})

    return JsonResponse({'success': False, 'error': 'Solicitud inválida'})

'''


def obtener_profesores(request):
    if request.method == 'GET':
        # Recuperar todos los profesores de la base de datos
        profesores = Profesores.objects.all().filter(Baja=False).values('id', 'Apellidos', 'Nombre').order_by(
            'Apellidos')

        # Crear una lista con los profesores en formato {'id': id, 'nombre': 'Apellidos, Nombre'}
        profesores_list = [
            {
                'id': profesor['id'],
                'nombre': f"{profesor['Apellidos']}, {profesor['Nombre']}"
            }
            for profesor in profesores
        ]

        # Devolver la lista en formato JSON
        return JsonResponse(profesores_list, safe=False)


def listar_item_guardia(request):
    curso_academico_actual = get_current_academic_year()
    # Obtener todos los items ordenados
    items = ItemGuardia.objects.filter(curso_academico=curso_academico_actual).order_by('-Fecha', 'ProfesorAusente',
                                                                                        'Tramo')

    # Inicializamos una lista para los items agrupados
    items_agrupados = []

    # Agrupamos por Fecha y ProfesorAusente
    for (fecha, profesor), group in groupby(items, key=lambda x: (x.Fecha, x.ProfesorAusente)):
        group_list = list(group)
        rowspan_fecha = len(group_list)  # Total de elementos en esta fecha
        rowspan_profesor = len(group_list)  # Total de elementos para este profesor en esta fecha

        for i, item in enumerate(group_list):
            # El primer item mostrará la fecha y el profesor, los demás no
            items_agrupados.append({
                'item': item,
                'mostrar_fecha': i == 0,  # Mostrar solo en el primer item
                'rowspan_fecha': rowspan_fecha,
                'mostrar_profesor': i == 0,  # Mostrar solo en el primer item
                'rowspan_profesor': rowspan_profesor,
            })

    return render(request, 'listar_item_guardia.html', {
        'items_agrupados': items_agrupados,
    })


def editar_item_guardia(request, pk):
    item = get_object_or_404(ItemGuardia, pk=pk)
    if request.method == 'POST':
        form = ItemGuardiaForm(request.POST, instance=item)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                print("Ya existe un ItemGuardia igual")

            return redirect('listar_item_guardia')
    else:
        form = ItemGuardiaForm(instance=item)

    return render(request, 'editar_item_guardia.html', {
        'form': form,
    })


def borrar_item_guardia(request, pk):
    item = get_object_or_404(ItemGuardia, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('listar_item_guardia')

    return render(request, 'confirmar_borrar_item_guardia.html', {
        'item': item,
    })


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def verausencias(request):
    curso_academico_actual = get_current_academic_year()
    # Buscar todos los ItemGuardia, sin filtrar por un profesor específico
    ausencias = ItemGuardia.objects.filter(curso_academico=curso_academico_actual).order_by('-Fecha')

    # Diccionario para agrupar por fecha y profesor
    ausencias_agrupadas = defaultdict(list)

    # Agrupar por fecha y profesor
    for ausencia in ausencias:
        key = (ausencia.Fecha, ausencia.ProfesorAusente)  # Agrupamos por fecha y profesor
        ausencias_agrupadas[key].append(ausencia)

    # Formatear los datos para la tabla
    datos_agrupados = []
    for (fecha, profesor), items in ausencias_agrupadas.items():
        dia_semana = dias_semana_es[fecha.strftime('%A')]  # Traducir día al español
        # dia_semana = fecha.strftime('%A').upper()
        datos_agrupados.append({
            'fecha': fecha.strftime('%d/%m/%Y'),  # Fecha en formato ISO para facilitar la consulta AJAX
            'diasemana': dia_semana,
            'tramos_ausente': len(items),  # Número de tramos ausente
            'profesor': profesor.__str__(),  # Nombre del profesor ausente
            'profesor_id': profesor.id
        })

    context = {
        'datos_agrupados': datos_agrupados,  # Enviamos los datos básicos de todas las ausencias
        'menu_guardias': True
    }

    return render(request, 'verausencias.html', context)


def eliminar_itemguardia_por_fecha(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        profesor_id = request.POST.get('profesor_id')
        curso_academico_actual = get_current_academic_year()

        # Convertir la fecha
        try:
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except ValueError:
            return JsonResponse({'error': 'Fecha no válida'}, status=400)

        # Obtener los ItemGuardia asociados a la fecha y al profesor
        profesor = get_object_or_404(Profesores, id=profesor_id)
        ItemGuardia.objects.filter(ProfesorAusente=profesor, Fecha=fecha,
                                   curso_academico=curso_academico_actual).delete()

        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


def obtener_tramos_guardia_por_fecha(request):
    fecha_str = request.GET.get('fecha')
    curso_academico_actual = get_current_academic_year()

    # Convertir la fecha
    try:
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha incorrecto.'}, status=400)

    profesor = request.user.profesor

    # Filtrar ItemGuardia para esa fecha y profesor
    itemguardias = ItemGuardia.objects.filter(ProfesorAusente=profesor, Fecha=fecha,
                                              curso_academico=curso_academico_actual)

    # Renderizar los tramos (similar a ItemHorario pero con la edición)
    html = render_to_string('partials/ausencia_items.html', {'items_guardia': itemguardias, 'fecha': fecha_str})

    return JsonResponse({'horario_html': html})


def horario_guardia_ajax(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':

        curso_academico_actual = get_current_academic_year()
        # Obtener los parámetros de la solicitud
        fecha_str = request.GET.get('fecha')
        profesor_id = request.user.profesor.id

        # Convertir la fecha a un objeto datetime
        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')

        # Obtener el día de la semana (1=Lunes, 2=Martes,...)
        dia_semana = fecha.isoweekday()

        # Filtrar los items de guardia según el profesor y el día de la semana
        items_guardia = ItemGuardia.objects.filter(ProfesorAusente_id=profesor_id, Fecha=fecha,
                                                   curso_academico=curso_academico_actual).order_by('Tramo')

        items_data = []
        for item in items_guardia:
            items_data.append({
                'id': item.id,
                'tramo_num': item.Tramo,  # Tramo numérico
                'tramo': dict(ItemGuardia.TRAMO_CHOICES).get(item.Tramo, f'Tramo {item.Tramo}'),  # Nombre del tramo
                'materia': item.Materia,
                'unidad': item.Unidad if item.Unidad else "N/A",  # Adaptar si Unidad es None
                'aula': item.Aula if item.Aula else "N/A",  # Adaptar si Aula es None
                'guardia_exists': True,  # Esto será siempre True ya que estamos mostrando guardias
                'tarea': item.Tarea
            })

        # Formatear la fecha
        # locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        # fecha_formateada = fecha.strftime("%A, %d de %B, %Y").capitalize()
        fecha_formateada = formatear_fecha(fecha)

        html = render_to_string('partials/ausencia_items.html',
                                {'items_horario': items_data, 'fecha': fecha_formateada})

        return JsonResponse({'horario_html': html})

    return JsonResponse({'error': 'Esta no es una solicitud AJAX.'})


def actualizar_ausencias_ajax(request):
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        profesor_ausente_id = request.POST.get('profesor_ausente')
        seleccionados = json.loads(request.POST.get('seleccionados', '[]'))
        no_seleccionados = json.loads(request.POST.get('no_seleccionados', '[]'))

        # Procesar los seleccionados (actualización o creación)
        for item_data in seleccionados:
            item_guardia_id = item_data.get('item_guardia_id')

            if item_guardia_id:  # Si existe el ID, actualizar el ItemGuardia
                item_guardia = get_object_or_404(ItemGuardia, id=item_guardia_id)
                item_guardia.Tarea = item_data['tarea']
                item_guardia.save()

        # Procesar los no seleccionados (eliminar los ItemGuardia)
        for item_guardia_id in no_seleccionados:
            item_guardia = get_object_or_404(ItemGuardia, id=item_guardia_id)
            item_guardia.delete()

        return JsonResponse({'success': True, 'message': 'Ausencias actualizadas correctamente.'})

    return JsonResponse({'error': 'Solicitud inválida.'})


def eliminar_itemguardia_por_fecha_y_profe(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        profesor_id = request.POST.get('profesor_id')
        curso_academico_actual = get_current_academic_year()

        # Convertir la fecha
        try:
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except ValueError:
            return JsonResponse({'error': 'Fecha no válida'}, status=400)

        # Obtener los ItemGuardia asociados a la fecha y al profesor
        profesor = get_object_or_404(Profesores, id=profesor_id)

        # Obtener los ItemGuardia asociados a la fecha y al profesor
        item_guardias = ItemGuardia.objects.filter(ProfesorAusente=profesor, Fecha=fecha,
                                                   curso_academico=curso_academico_actual)

        # Eliminar los tiempos de guardia asociados a esos ItemGuardia
        for item_guardia in item_guardias:
            TiempoGuardia.objects.filter(item_guardia=item_guardia).delete()

        # Eliminar los ItemGuardia
        item_guardias.delete()

        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


def eliminar_itemguardia_por_fecha_profe_y_tramo(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        profesor_id = request.POST.get('profesor_id')
        tramo = request.POST.get('tramo')
        curso_academico_actual = get_current_academic_year()

        # Convertir la fecha
        try:
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
        except ValueError:
            return JsonResponse({'error': 'Fecha no válida'}, status=400)

        # Obtener los ItemGuardia asociados a la fecha y al profesor
        profesor = get_object_or_404(Profesores, id=profesor_id)

        # Obtener los ItemGuardia asociados a la fecha y al profesor
        item_guardia = ItemGuardia.objects.filter(ProfesorAusente=profesor, Fecha=fecha, Tramo=tramo,
                                                  curso_academico=curso_academico_actual)

        # Eliminar los tiempos de guardia asociados a esos ItemGuardia
        if item_guardia.exists():
            TiempoGuardia.objects.filter(item_guardia__in=item_guardia).delete()  # Borrar los tiempos relacionados
            item_guardia.delete()  # Borrar los ItemGuardia

        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def estadisticas(request):
    # Obtener todos los cursos académicos
    cursos_academicos = CursoAcademico.objects.order_by('nombre')

    # Determinar el curso académico seleccionado
    curso_academico_id = request.GET.get('curso_academico')
    if curso_academico_id:
        curso_seleccionado = get_object_or_404(CursoAcademico, id=curso_academico_id)
    else:
        curso_seleccionado = get_current_academic_year()

    # Por defecto, mostrar el curso académico actual si no se selecciona uno
    if not curso_seleccionado:
        curso_seleccionado = get_current_academic_year()

    if request.method == "POST":
        try:
            f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
            f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')
        except (ValueError, TypeError):
            # Manejar errores de fechas inválidas
            f1, f2 = None, None
    else:
        f1, f2 = None, None

    # Estadísticas por tramo horario
    lista_tramos = []
    horas = ["[1ª] Primera", "[2ª] Segunda", "[3ª] Tercera", "Recreo", "[4ª] Cuarta", "[5ª] Quinta", "[6ª] Sexta"]
    for i in range(1, 8):
        if f1 and f2:  # Si se han enviado fechas válidas
            lista_tramos.append(ItemGuardia.objects.filter(Tramo=i, Fecha__gte=f1, Fecha__lte=f2,
                                                           curso_academico=curso_seleccionado).count())
        else:
            lista_tramos.append(ItemGuardia.objects.filter(Tramo=i, curso_academico=curso_seleccionado).count())
    horas.append("TOTAL")
    if f1 and f2:
        lista_tramos.append(
            ItemGuardia.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
    else:
        lista_tramos.append(ItemGuardia.objects.filter(curso_academico=curso_seleccionado).count())

    # Estadísticas por día de la semana
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    lista_dias_semana = []
    for i in range(1, 6):  # Días de la semana (1: Lunes, 5: Viernes)
        if f1 and f2:
            lista_dias_semana.append(ItemGuardia.objects.filter(Fecha__gte=f1, Fecha__lte=f2,
                                                                Fecha__week_day=i + 1,  # Django Sunday = 1
                                                                curso_academico=curso_seleccionado).count())
        else:
            lista_dias_semana.append(ItemGuardia.objects.filter(Fecha__week_day=i + 1,
                                                                curso_academico=curso_seleccionado).count())

    # Estadísticas por mes

    meses_labels = ['Septiembre', 'Octubre', 'Noviembre', 'Diciembre', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo',
                    'Junio']
    lista_meses = []

    for mes in range(9, 13):  # Meses del año actual (Septiembre a Diciembre)
        if request.method == "POST":
            lista_meses.append(ItemGuardia.objects.filter(Fecha__month=mes, Fecha__gte=f1, Fecha__lte=f2,
                                                          curso_academico=curso_seleccionado).count())
        else:
            lista_meses.append(ItemGuardia.objects.filter(Fecha__month=mes, curso_academico=curso_seleccionado).count())

    for mes in range(1, 7):  # Meses del siguiente año (Enero a Junio)
        if request.method == "POST":
            lista_meses.append(ItemGuardia.objects.filter(Fecha__month=mes, Fecha__gte=f1, Fecha__lte=f2,
                                                          curso_academico=curso_seleccionado).count())
        else:
            lista_meses.append(ItemGuardia.objects.filter(Fecha__month=mes, curso_academico=curso_seleccionado).count())

        # Obtener estadísticas por profesor (solo aquellos con ausencias)
    if f1 and f2:
        profesores_con_ausencias = ItemGuardia.objects.filter(Fecha__gte=f1, Fecha__lte=f2,
                                                              curso_academico=curso_seleccionado) \
            .values('ProfesorAusente__Apellidos', 'ProfesorAusente__Nombre') \
            .annotate(total_ausencias=Count('ProfesorAusente')) \
            .order_by('-total_ausencias')
    else:
        profesores_con_ausencias = ItemGuardia.objects.filter(curso_academico=curso_seleccionado) \
            .values('ProfesorAusente__Apellidos', 'ProfesorAusente__Nombre') \
            .annotate(total_ausencias=Count('ProfesorAusente')) \
            .order_by('-total_ausencias')

        # Preparar datos para el gráfico de profesores
    profesores_labels = [f"{prof['ProfesorAusente__Apellidos']}, {prof['ProfesorAusente__Nombre']}" for prof in
                         profesores_con_ausencias]
    profesores_data = [prof['total_ausencias'] for prof in profesores_con_ausencias]

    # Formulario para las fechas
    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)

    # Contexto para la plantilla
    context = {
        'form': form,
        'horas': zip(horas, lista_tramos),
        'dias_semana': zip(dias_semana, lista_dias_semana),
        'dias_semana_labels': dias_semana,  # Etiquetas de los días
        'dias_semana_data': lista_dias_semana,  # Datos de ausencias por día
        'meses_labels': meses_labels,  # Etiquetas de los meses
        'meses_data': lista_meses,  # Datos de ausencias por mes
        'meses': zip(meses_labels, lista_meses),
        'profesores_con_ausencias': profesores_con_ausencias,
        'profesores_labels': profesores_labels,
        'profesores_data': profesores_data,
        'curso_seleccionado': curso_seleccionado,
        'cursos_academicos': cursos_academicos,
        'totales': lista_tramos,
        'menu_estadistica': True
    }

    return render(request, 'estadisticasguardias.html', context)


def actualizar_guardia_ajax(request):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Obtener los datos enviados mediante POST
        item_guardia_id = request.POST.get('item_guardia_id')
        profesor_confirma_id = request.POST.get('profesor_confirma_id')

        # Deserializar la cadena JSON de 'profesores_guardia_data' en una lista de diccionarios
        profesores_guardia_data = json.loads(request.POST.get('profesores_guardia_data', '[]'))

        try:
            # Obtener el ItemGuardia que se va a actualizar
            item_guardia = ItemGuardia.objects.get(id=item_guardia_id)

            # Crear una lista de IDs de profesores para asignarlos a ProfesoresGuardia en el ItemGuardia
            profesores_guardia_ids = [profesor['profesor_id'] for profesor in profesores_guardia_data]

            # Obtener los objetos de los profesores seleccionados
            profesores_guardia = Profesores.objects.filter(id__in=profesores_guardia_ids)

            # Actualizar los campos correspondientes en ItemGuardia
            item_guardia.ProfesoresGuardia.set(profesores_guardia)  # Asignar los profesores seleccionados
            item_guardia.ProfesorConfirma_id = profesor_confirma_id  # Asignar el profesor que confirmó
            item_guardia.save()

            # Eliminar los registros previos de TiempoGuardia para este ItemGuardia, evitando duplicados
            TiempoGuardia.objects.filter(item_guardia=item_guardia).delete()

            # Reasignar el tiempo específico a cada profesor
            for profesor_data in profesores_guardia_data:
                profesor_id = profesor_data.get('profesor_id')
                tiempo_asignado = profesor_data.get('tiempo_asignado')

                # Obtener el objeto Profesor
                profesor = Profesores.objects.get(id=profesor_id)

                # Crear el nuevo registro en TiempoGuardia con el tiempo específico
                TiempoGuardia.objects.create(
                    profesor=profesor,
                    dia_semana=item_guardia.Fecha.weekday() + 1,  # 1:Lunes, 2:Martes, etc.
                    tramo=item_guardia.Tramo,
                    tiempo_asignado=tiempo_asignado,
                    item_guardia=item_guardia
                )

                # Crear también el tiempo para el profesor sustituto o titular, si existe
                if profesor.SustitutoDe:
                    TiempoGuardia.objects.create(
                        profesor=profesor.SustitutoDe,
                        dia_semana=item_guardia.Fecha.weekday() + 1,
                        tramo=item_guardia.Tramo,
                        tiempo_asignado=tiempo_asignado,
                        item_guardia=item_guardia
                    )
                else:
                    try:
                        sustituto = Profesores.objects.get(SustitutoDe=profesor)
                        TiempoGuardia.objects.create(
                            profesor=sustituto,
                            dia_semana=item_guardia.Fecha.weekday() + 1,
                            tramo=item_guardia.Tramo,
                            tiempo_asignado=tiempo_asignado,
                            item_guardia=item_guardia
                        )
                    except Profesores.DoesNotExist:
                        pass

            return JsonResponse({'success': True})

        except ItemGuardia.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ItemGuardia no encontrado'})

    return JsonResponse({'success': False, 'error': 'Solicitud inválida'})


def modal_registrar_ausencia(request):
    return render(request, "partials/modal_registrar_ausencia.html")

@login_required(login_url='/')
@user_passes_test(group_check_je_or_conserjes, login_url='/')
def verausencias_hoy(request):
    curso_academico_actual = get_current_academic_year()
    hoy = date.today()  # Día actual

    # Filtrar solo ausencias de hoy
    ausencias_hoy = ItemGuardia.objects.filter(
        curso_academico=curso_academico_actual,
        Fecha=hoy
    ).order_by('TramoHorario', 'ProfesorAusente__first_name')

    # Organiza las ausencias por tramo
    guardias_por_tramo = defaultdict(list)
    tramos = ["1", "2", "3", "rec", "4", "5", "6"]  # Ajusta según tus claves reales

    for ausencia in ausencias_hoy:
        guardias_por_tramo[str(ausencia.TramoHorario)].append(ausencia)

    context = {
        'tramos': tramos,
        'guardias_por_tramo': guardias_por_tramo,
        'menu_guardias': True
    }
    return render(request, 'dashboard.html', context)
