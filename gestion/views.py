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

import os
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import render,redirect
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate,login
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection

from centro.models import Alumnos, Cursos, MateriaImpartida, Profesores
from centro.utils import importar_profesores, get_current_academic_year
from centro.views import is_tutor, group_check_je, group_check_je_or_conserjes
from convivencia.models import Amonestaciones, Sanciones, PropuestasSancion, IntervencionAulaHorizonte
from convivencia.views import calcular_alumnado_sancionable, ContarFaltas, ContarFaltasHistorico
from gestion.forms import CustomPasswordChangeForm, QueryForm
from guardias.models import ItemGuardia
from horarios.models import ItemHorario
from reservas.models import Reservas


# Create your views here.

# Vista de cambio de contraseña
@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantiene la sesión activa después del cambio de contraseña
            messages.success(request, 'Tu contraseña se ha cambiado con éxito.')
            # Actualiza el campo en el modelo Profesores
            if hasattr(request.user, 'profesor'):
                request.user.profesor.password_changed = True
                request.user.profesor.save()
            return redirect('index')  # Redirige al índice o a otra vista adecuada
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'cambiar_password.html', {'form': form})


@login_required
def cambiar_password_custom(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantiene la sesión activa después del cambio de contraseña
            messages.success(request, 'Tu contraseña se ha cambiado con éxito.')
            # Actualiza el campo en el modelo Profesores
            if hasattr(request.user, 'profesor'):
                request.user.profesor.password_changed = True
                request.user.profesor.save()
            return redirect('index')  # Redirige al índice o a otra vista adecuada
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'cambiar_password_custom.html', {'form': form})

# Curro Jul 24: Simplifico el index y dejo la logica para el login_view
@login_required(login_url='/login/')
def index(request):
    user = request.user
    curso_academico_actual = get_current_academic_year()


    if user.groups.filter(name='conserjes').exists():
        return redirect(reverse('dashboard_conserjes'))


    # Verificar cambio de contraseña para roles normales (excluyendo superuser y jefatura)
    if not user.is_superuser and not user.groups.filter(name='jefatura de estudios').exists():
        if not hasattr(user, 'profesor') or not user.profesor.password_changed:
            return redirect(reverse('cambiar_password'))

    # Redirigir a dashboard jefatura si pertenece al grupo
    if user.groups.filter(name='jefatura de estudios').exists():
        return redirect(reverse('dashboard_jefatura'))


    profesor = request.user.profesor
    hoy = date.today()

    # Curso académico actual
    curso_actual = get_current_academic_year()

    # Unidades donde el profesor está en el equipo educativo, ahora usando MateriaImpartida
    materias_impartidas = MateriaImpartida.objects.filter(profesor=profesor, curso_academico=curso_actual)
    unidades = [materia_impartida.curso for materia_impartida in materias_impartidas]

    # Alumnos de esas unidades
    alumnos = []
    for unidad in unidades:
        alumnos.extend(unidad.alumnos_set.all())

    # Amonestaciones de hoy
    amonestaciones_hoy = Amonestaciones.objects.filter(
        IdAlumno__in=alumnos,
        Fecha=hoy,
        curso_academico=curso_actual
    ).select_related('IdAlumno')

    # Alumnos sancionados hoy
    sanciones = Sanciones.objects.filter(
        IdAlumno__in=alumnos,
        Fecha__lte=hoy,
        Fecha_fin__gte=hoy,
        curso_academico=curso_actual
    ).select_related('IdAlumno')

    tramos = ['1', '2', '3', 'rec', '4', '5', '6']

    horario_hoy = []
    tramos_horarios = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']
    dia_semana = date.today().isoweekday()  # 1 (lunes) - 7 (domingo)

    if profesor:

        if dia_semana in range(1, 6):  # Solo lunes a viernes
            items_hoy = ItemHorario.objects.filter(profesor=profesor, dia=dia_semana, curso_academico=curso_academico_actual).order_by('tramo')
            # Agrupar por tramo como en tu vista de horario
            items_por_tramo = {tramo: [] for tramo in range(1, 8)}
            for item in items_hoy:
                # Agrupar por materia/unidad/aula iguales
                for existing in items_por_tramo[item.tramo]:
                    if existing.materia == item.materia and existing.aula == item.aula:
                        existing.unidades_combinadas += f", {item.unidad}"
                        break
                else:
                    item.unidades_combinadas = str(item.unidad)
                    items_por_tramo[item.tramo].append(item)

            horario_hoy = [(tramos_horarios[tramo - 1], items_por_tramo[tramo]) for tramo in range(1, 8)]

    reservas_hoy = []
    if profesor:
        reservas_hoy = Reservas.objects.filter(Profesor=profesor, Fecha=hoy).order_by('Hora')

    tramo_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "rec": 4,
        "4": 5,
        "5": 6,
        "6": 7,
    }

    # Agrupa ausencias por tramo
    guardias_por_tramo = {}
    for tramo_name in tramos:
        item_guardias = ItemGuardia.objects.filter(
            Fecha=hoy,
            Tramo=tramo_map[tramo_name],
            curso_academico=curso_academico_actual,
        ).select_related('Unidad', 'Aula', 'ProfesorAusente')
        guardias_por_tramo[tramo_name] = item_guardias

    contexto = {
        'amonestaciones_hoy': amonestaciones_hoy,
        'sanciones_hoy': sanciones,
        'tramos': tramos,
        'horario_hoy': horario_hoy,
        'reservas_hoy': reservas_hoy,
        'guardias_por_tramo': guardias_por_tramo,
    }

    return render(request, 'index.html', contexto)


@login_required(login_url='/login/')
@user_passes_test(group_check_je, login_url='/')
def dashboard_jefatura(request):
    curso_actual = get_current_academic_year()

    # --- Alumnado sancionable ---
    ver_ignoradas = False  # O cambiar según lógica que quieras
    datos = calcular_alumnado_sancionable(curso_actual)

    resultado = []

    # Cargar propuestas sanción abiertas (sin salida)
    propuestas = PropuestasSancion.objects.filter(
        curso_academico=curso_actual,
        salida=None
    ).all()

    alumnos_en_propuestas = [p.alumno for p in propuestas]
    nuevos_alumnos = [a for a in datos if a not in alumnos_en_propuestas]

    # Añadir nuevas propuestas por alumnos que no estaban registrados
    for alumno in nuevos_alumnos:
        propuesta = PropuestasSancion(
            curso_academico=curso_actual,
            alumno=alumno,
            leves=datos[alumno]['leves'],
            graves=datos[alumno]['graves'],
            peso=datos[alumno]['peso'],
            entrada=datos[alumno]['entrada']
        )
        propuesta.save()
        ultima_amonestacion = Amonestaciones.objects.filter(
            IdAlumno=alumno,
            curso_academico=curso_actual
        ).order_by('-Fecha').first()

        resultado.append((
            alumno,
            datos[alumno]['leves'],
            datos[alumno]['graves'],
            datos[alumno]['peso'],
            ultima_amonestacion.Fecha if ultima_amonestacion else None,
            propuesta.id,
            propuesta.ignorar,
            datos[alumno].get('móvil', False)
        ))

    # Actualizar propuestas existentes
    for propuesta in propuestas:
        alumno = propuesta.alumno
        if alumno not in datos:
            # Alumno ya no sancionable, marcar salida
            propuesta.salida = date.today()
            propuesta.motivo_salida = "Amonestaciones prescritas."
            propuesta.save()
            continue

        # Actualizar datos según estado de ignorar
        if propuesta.ignorar and datos[alumno]['peso'] <= propuesta.peso:
            propuesta.leves = datos[alumno]['leves']
            propuesta.graves = datos[alumno]['graves']
            propuesta.peso = datos[alumno]['peso']
            propuesta.save()
        else:
            propuesta.ignorar = False
            propuesta.leves = datos[alumno]['leves']
            propuesta.graves = datos[alumno]['graves']
            propuesta.peso = datos[alumno]['peso']
            propuesta.save()

        if not propuesta.ignorar or ver_ignoradas:
            ultima_amonestacion = Amonestaciones.objects.filter(
                IdAlumno=alumno,
                curso_academico=curso_actual
            ).order_by('-Fecha').first()
            resultado.append((
                alumno,
                datos[alumno]['leves'],
                datos[alumno]['graves'],
                datos[alumno]['peso'],
                ultima_amonestacion.Fecha if ultima_amonestacion else None,
                propuesta.id,
                propuesta.ignorar,
                datos[alumno].get('móvil', False)
            ))

    resultado.sort(key=lambda x: (int(x[7]), x[3], x[2], x[1]), reverse=True)

    # --- Derivaciones Aula Horizonte ---
    amonestaciones = Amonestaciones.objects.filter(
        DerivadoConvivencia=True,
        curso_academico=curso_actual
    ).select_related('IdAlumno', 'Profesor', 'IdAlumno__Unidad')

    intervenciones = IntervencionAulaHorizonte.objects.filter(
        curso_academico=curso_actual
    )

    intervenciones_indexadas = set(
        (i.alumno_id, i.fecha, i.tramo_horario, i.profesor_envia_id)
        for i in intervenciones
    )

    for amon in amonestaciones:
        clave = (amon.IdAlumno_id, amon.Fecha, amon.Hora, amon.Profesor_id)
        amon.tiene_intervencion = clave in intervenciones_indexadas

    intervenciones = (
        IntervencionAulaHorizonte.objects
        .filter(curso_academico=curso_actual)
        .select_related('alumno', 'alumno__Unidad', 'profesor_envia', 'profesor_atiende')
        .order_by('-fecha')[:10]  # Mostrar solo las últimas 50 para performance en widget
    )

    profesores = Profesores.objects.filter(Baja=False)
    cursos = Cursos.objects.all()

    profesor = request.user.profesor
    hoy = date.today()
    manana = hoy + timedelta(days=1)



    tramos = ['1', '2', '3', 'rec', '4', '5', '6']

    horario_hoy = []
    tramos_horarios = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']
    dia_semana = date.today().isoweekday()  # 1 (lunes) - 7 (domingo)

    if profesor:

        if dia_semana in range(1, 6):  # Solo lunes a viernes
            items_hoy = ItemHorario.objects.filter(profesor=profesor, dia=dia_semana,
                                                   curso_academico=curso_actual).order_by('tramo')
            # Agrupar por tramo como en tu vista de horario
            items_por_tramo = {tramo: [] for tramo in range(1, 8)}
            for item in items_hoy:
                # Agrupar por materia/unidad/aula iguales
                for existing in items_por_tramo[item.tramo]:
                    if existing.materia == item.materia and existing.aula == item.aula:
                        existing.unidades_combinadas += f", {item.unidad}"
                        break
                else:
                    item.unidades_combinadas = str(item.unidad)
                    items_por_tramo[item.tramo].append(item)

            horario_hoy = [(tramos_horarios[tramo - 1], items_por_tramo[tramo]) for tramo in range(1, 8)]

    reservas_hoy = []
    if profesor:
        reservas_hoy = Reservas.objects.filter(Profesor=profesor, Fecha=hoy).order_by('Hora')

    tramo_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "rec": 4,
        "4": 5,
        "5": 6,
        "6": 7,
    }

    # Agrupa ausencias por tramo
    guardias_por_tramo = {}
    for tramo_name in tramos:
        item_guardias = ItemGuardia.objects.filter(
            Fecha=hoy,
            Tramo=tramo_map[tramo_name],
            curso_academico=curso_actual,
        ).select_related('Unidad', 'Aula', 'ProfesorAusente')
        guardias_por_tramo[tramo_name] = item_guardias

        # Filtrar reservas solo para hoy y mañana, y solo tipo "Espacio"
        lista_reservas = Reservas.objects.filter(
            curso_academico=curso_actual,
            Fecha__in=[hoy, manana],
            Reservable__TiposReserva__TipoReserva='Espacio'
        ).order_by('Fecha')

        reservas_info = []
        for reserva in lista_reservas:
            item_horario = ItemHorario.objects.filter(
                profesor=reserva.Profesor,
                dia=reserva.Fecha.weekday() + 1,  # lunes=0, offset +1
                tramo=int(reserva.Hora)
            ).first()

            reservas_info.append({
                'r': reserva,
                'curso': item_horario.unidad if item_horario else None,
                'aula': item_horario.aula if item_horario else None,
            })

    tipo = 'amonestacion'  # o 'sancion' según widget; puedes parametrizar si quieres

    if tipo == 'amonestacion':
        datos_qs = Amonestaciones.objects.filter(Fecha=hoy)
        titulo = "Resumen de amonestaciones hoy"
    else:
        datos_qs = Sanciones.objects.filter(Fecha=hoy)
        titulo = "Resumen de sanciones hoy"

    datos = list(datos_qs)
    datos_en_zip = zip(range(1, len(datos) + 1), datos, ContarFaltas(datos_qs.values("IdAlumno")),
                       ContarFaltasHistorico(datos_qs.values("IdAlumno")))

    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]

    # Alumnos sancionados hoy
    sanciones_alumnado = Sanciones.objects.filter(
        Fecha__lte=hoy,
        Fecha_fin__gte=hoy,
        curso_academico=curso_actual
    ).select_related('IdAlumno')



    contexto = {
        'alumnado': resultado,
        'num_resultados': len(resultado),
        'intervenciones': intervenciones,
        'amonestaciones': amonestaciones,
        'profesores': profesores,
        'cursos': cursos,
        'ver_ignoradas': ver_ignoradas,
        'tramos': tramos,
        'horario_hoy': horario_hoy,
        'guardias_por_tramo': guardias_por_tramo,
        'reservas_info': reservas_info,
        'datos': datos_en_zip,
        'tipo': tipo,
        'titulo': titulo,
        'horas': horas,
        'sanciones_alumnado': sanciones_alumnado
    }

    return render(request, 'indexje.html', contexto)




@login_required(login_url='/login/')
@user_passes_test(group_check_je_or_conserjes, login_url='/')
def dashboard_conserjes(request):
    curso_actual = get_current_academic_year()



    profesores = Profesores.objects.filter(Baja=False)
    cursos = Cursos.objects.all()

    hoy = date.today()
    manana = hoy + timedelta(days=1)



    tramos = ['1', '2', '3', 'rec', '4', '5', '6']

    horario_hoy = []
    tramos_horarios = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']
    dia_semana = date.today().isoweekday()  # 1 (lunes) - 7 (domingo)



    tramo_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "rec": 4,
        "4": 5,
        "5": 6,
        "6": 7,
    }

    # Agrupa ausencias por tramo
    guardias_por_tramo = {}
    for tramo_name in tramos:
        item_guardias = ItemGuardia.objects.filter(
            Fecha=hoy,
            Tramo=tramo_map[tramo_name],
            curso_academico=curso_actual,
        ).select_related('Unidad', 'Aula', 'ProfesorAusente')
        guardias_por_tramo[tramo_name] = item_guardias



    contexto = {

        'profesores': profesores,
        'cursos': cursos,
        'tramos': tramos,
        'horario_hoy': horario_hoy,
        'guardias_por_tramo': guardias_por_tramo,
    }

    return render(request, 'indexcons.html', contexto)


@login_required(login_url='/')
def salir(request):
    logout(request)
    return redirect('/')

# Curro Jul 24: Defino la vista para el login
def login_view(request):
    context = {'next': request.GET.get('next', '/')}
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            #if not user.groups.filter(name__in=['jefatura de estudios']):
            if not user.is_superuser:
                # Verifica si el usuario tiene un perfil de Profesor y si debe cambiar la contraseña
                if hasattr(user, 'profesor') and not user.profesor.password_changed:
                    return redirect(reverse('cambiar_password'))

            next_url = request.POST.get("next", "/")
            return redirect(next_url)
        else:
            context['error'] = True

    return render(request, 'login.html', context)


def descargar_base_datos(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("No tienes permiso para descargar la base de datos.")

    # Ruta al archivo de la base de datos
    db_path = settings.DATABASES['default']['NAME']
    response = FileResponse(open(db_path, 'rb'), as_attachment=True, filename=os.path.basename(db_path))
    return response


@staff_member_required
def cargar_qry(request):
    result = None
    error = None
    columnas = None
    if request.method == "POST":
        form = QueryForm(request.POST)
        if form.is_valid():
            print(form.cleaned_data)
            query = form.cleaned_data["query"]

            print(query)
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    if query.strip().lower().startswith("select"):
                        columnas = [col[0] for col in cursor.description]
                        print(columnas)
                        columnas = cursor.description
                        result = cursor.fetchall()
            except Exception as e:
                error = str(e)
        else:
            print(form.errors)
            print(form.cleaned_data)
    else:
        form = QueryForm()

    return render(request, "cargar_qry.html", {"form": form, "result": result, "columnas": columnas, "error": error})

