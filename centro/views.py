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


import csv
import io
import json
import os
import time
from collections import defaultdict

import unicodedata
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.checks.urls import check_url_settings
from django.db import transaction
from django.db.models import Q, Count
from django.forms import modelformset_factory
from django.http import HttpResponseForbidden, FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from centro.models import Alumnos, Cursos, Departamentos, Profesores, Niveles, Materia, MateriaImpartida, \
    MatriculaMateria, LibroTexto, MomentoRevisionLibros, RevisionLibroAlumno, EstadoLibro, RevisionLibro, \
    CursoAcademico, PreferenciaHorario
from centro.utils import get_current_academic_year, get_previous_academic_years
from convivencia.models import Amonestaciones, Sanciones
from centro.forms import UnidadForm, DepartamentosForm, UnidadProfeForm, UnidadesProfeForm, SeleccionRevisionForm, \
    RevisionLibroAlumnoForm, SeleccionRevisionProfeForm, ProfesorSustitutoForm
from datetime import datetime, timedelta

from gestion import settings
from guardias.models import ItemGuardia, TiempoGuardia
from horarios.models import ItemHorario


def group_check_je(user):
    return user.groups.filter(name__in=['jefatura de estudios'])


# Curro Jul 24
def group_check_je(user):
    return user.groups.filter(name__in=['jefatura de estudios'])


def group_check_tde(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'tde']).exists()


def group_check_prof(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'profesor']).exists()


def group_check_prof_or_guardia(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'profesor', 'guardia']).exists()

def group_check_prof_or_guardia_or_conserje(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'profesor', 'guardia', 'conserjes']).exists()


def group_check_prof_and_tutor(user):
    return group_check_prof(user) and is_tutor(user)


def group_check_prof_and_tutor_or_je(user):
    return group_check_prof_and_tutor(user) or group_check_je(user)


def group_check_je_or_orientacion(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'orientacion']).exists()

def group_check_je_or_dace(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'dace']).exists()


def group_check_prof_and_tutor_or_je_or_orientacion(user):
    return group_check_prof_and_tutor(user) or group_check_je_or_orientacion(user)

def group_check_je_or_conserjes(user):
    return user.groups.filter(name__in=['jefatura de estudios', 'conserjes']).exists()


def is_tutor(user):
    # Comprueba si el usuario tiene un perfil de profesor asociado
    if hasattr(user, 'profesor'):
        profesor = user.profesor
        # Comprueba si el profesor es tutor de algún curso
        return Cursos.objects.filter(Tutor_id=profesor.id).exists()

    return False


# Create your views here.


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def alumnos(request):
    if request.method == 'POST':
        primer_id = request.POST.get("Unidad")
    else:
        try:
            primer_id = request.session.get('Unidad', Cursos.objects.all().first().id)
        except:
            primer_id = 0

    request.session['Unidad'] = primer_id

    lista_alumnos = Alumnos.objects.filter(Unidad__id=primer_id)
    lista_alumnos = sorted(lista_alumnos, key=lambda d: d.Nombre)
    ids = [{"id": elem.id} for elem in lista_alumnos]

    form = UnidadForm({'Unidad': primer_id})
    lista = zip(lista_alumnos, ContarFaltas(ids), ContarFaltasHistorico(ids), EstaSancionado(ids))
    try:
        context = {'alumnos': lista, 'form': form, 'curso': Cursos.objects.get(id=primer_id), 'menu_convivencia': True}
    except:
        context = {'alumnos': lista, 'form': form, 'curso': None, 'menu_convivencia': True}
    return render(request, 'alumnos.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def alumnos_curso(request, curso):
    request.POST = request.POST.copy()
    request.POST["Unidad"] = curso
    request.method = "POST"
    return alumnos(request)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def profesores(request):
    if request.method == 'POST':
        dep_id = request.POST.get("Departamento")
        area_id = request.POST.get("Areas")
        if area_id != request.session.get("Areas", ""):
            dep_id = ""
    else:
        dep_id = request.session.get('Departamento', "")
        area_id = request.session.get("Areas", "")

    request.session['Areas'] = area_id
    request.session['Departamento'] = dep_id
    form = DepartamentosForm({'Areas': area_id, 'Departamento': dep_id})
    if dep_id == "":
        lista_profesores = Profesores.objects.filter(Baja=False).order_by("Apellidos")
        departamento = ""
    else:
        lista_profesores = Profesores.objects.filter(Departamento__id=dep_id, Baja=False).order_by("Apellidos")
        departamento = Departamentos.objects.get(id=dep_id).Nombre

    cursos = Tutorias(lista_profesores.values("id"))
    lista = zip(lista_profesores, cursos)
    context = {'profesores': lista, 'form': form, "departamento": departamento, 'menu_profesor': True}
    return render(request, 'profesor.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def profesores_change(request, codigo, operacion):
    dato = {}
    dato["Baja"] = True if operacion == "on" else False
    Profesores.objects.filter(id=codigo).update(**dato)

    return redirect("/centro/profesores")


def Tutorias(lista_id):
    cursos = []
    for prof in lista_id:
        try:
            cursos.append(Cursos.objects.get(Tutor=prof.values()[0]).Curso)
        except:
            cursos.append("")
    return cursos


def EstaSancionado(lista_id):
    estasancionado = []
    hoy = datetime.now()
    dict = {}
    dict["Fecha_fin__gte"] = hoy
    dict["Fecha__lte"] = hoy
    sanc = Sanciones.objects.filter(**dict).order_by("Fecha")
    listaid = [x.IdAlumno.id for x in sanc]
    for alum in lista_id:
        if list(alum.values())[0] in listaid:
            estasancionado.append(True)
        else:
            estasancionado.append(False)
    return estasancionado


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def cursos(request):
    lista_cursos = Cursos.objects.all()
    context = {'cursos': lista_cursos, 'menu_cursos': True}
    return render(request, 'cursos.html', context)


# Curro Jul 24: Redefino la vista misalumnos
@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misalumnos(request):
    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor
    curso_academico = get_current_academic_year()

    # Obtener los cursos donde el profesor imparte materias en el curso académico actual
    cursos = Cursos.objects.filter(materiaimpartida__profesor=profesor, materiaimpartida__curso_academico=curso_academico)
    cursos_resto = Cursos.objects.exclude(materiaimpartida__profesor=profesor, materiaimpartida__curso_academico=curso_academico)

    if request.method == 'POST':
        if request.POST.get("FormTrigger") == "Unidad":
            primer_id = request.POST.get("Unidad")
        else:
            primer_id = request.POST.get("UnidadResto")
    else:
        try:
            primer_id = cursos.order_by('Curso').first().id
        except:
            primer_id = 0

    request.session['Unidad'] = primer_id

    # Obtener los alumnos del curso seleccionado
    lista_alumnos = Alumnos.objects.filter(Unidad__id=primer_id)
    lista_alumnos = sorted(lista_alumnos, key=lambda d: d.Nombre)
    ids = [{"id": elem.id} for elem in lista_alumnos]

    # Crear el formulario con los cursos del profesor
    form = UnidadesProfeForm({'Unidad': request.POST.get("Unidad"), 'UnidadResto': request.POST.get("UnidadResto")},
                             profesor=profesor, curso_academico=curso_academico)

    # Preparar el listado de alumnos y sus estadísticas
    lista = zip(lista_alumnos, ContarFaltas(ids), ContarFaltasHistorico(ids), EstaSancionado(ids))

    # Contexto para la plantilla
    try:
        context = {
            'alumnos': lista,
            'form': form,
            'curso': Cursos.objects.get(id=primer_id),
            'menu_convivencia': True,
            'profesor': profesor
        }
    except:
        context = {
            'alumnos': lista,
            'form': form,
            'curso': None,
            'menu_convivencia': True,
            'profesor': profesor
        }

    return render(request, 'misalumnos.html', context)


def obtener_tramo_actual():
    ahora = datetime.now()
    minutos_actuales = ahora.hour * 60 + ahora.minute
    dia_actual = ahora.isoweekday()  # Lunes=1, Domingo=7, compatible con tu modelo

    tramos = [
        (1, 8*60+15, 9*60+15),
        (2, 9*60+15, 10*60+15),
        (3, 10*60+15, 11*60+15),
        (4, 11*60+15, 11*60+45),  # Recreo
        (5, 11*60+45, 12*60+45),
        (6, 12*60+45, 13*60+45),
        (7, 13*60+45, 14*60+45),
    ]

    for tramo, inicio, fin in tramos:
        if inicio <= minutos_actuales < fin:
            return dia_actual, tramo
    return dia_actual, None

@login_required(login_url='/')
@user_passes_test(group_check_je_or_conserjes, login_url='/')
def busqueda(request):
    query = ""
    resultados_actuales = []
    resultados_antiguos = []
    num_resultados = 0
    tiempo_busqueda = 0
    curso_actual = get_current_academic_year()

    if request.method == 'POST':
        query = request.POST.get('q')
        if query:
            query_normalizada = normalizar_texto(query)
            start_time = time.time()

            resultados = Alumnos.objects.all()
            resultados = [
                alumno for alumno in resultados
                if query_normalizada in normalizar_texto(alumno.Nombre) or
                   query_normalizada in (alumno.DNI or '').lower() or
                   query_normalizada in (alumno.NIE or '').lower() or
                   query_normalizada in normalizar_texto(alumno.email)
            ]

            end_time = time.time()
            tiempo_busqueda = round(end_time - start_time, 2)
            resultados_actuales = [a for a in resultados if a.Unidad]
            resultados_antiguos = [a for a in resultados if not a.Unidad]

            dia, tramo = obtener_tramo_actual()

            # Añadir localización
            for alumno in resultados_actuales:
                alumno.localizaciones = []
                if not tramo:
                    continue
                matriculas = MatriculaMateria.objects.filter(alumno=alumno, curso_academico=curso_actual)
                for m in matriculas:
                    imp = m.materia_impartida
                    print(dia)
                    print(tramo)
                    items = ItemHorario.objects.filter(
                        unidad=imp.curso,
                        profesor=imp.profesor,
                        dia=dia,
                        tramo=tramo,
                        curso_academico=curso_actual
                    )
                    for item in items:
                        alumno.localizaciones.append({
                            'aula': item.aula.Aula,
                            'materia': imp.materia.nombre,
                            'profesor': str(imp.profesor)
                        })



            num_resultados = len(resultados)

    context = {
        'resultados_actuales': resultados_actuales,
        'resultados_antiguos': resultados_antiguos,
        'query': query,
        'num_resultados': num_resultados,
        'tiempo_busqueda': tiempo_busqueda,
        'menu_convivencia': True
    }
    return render(request, 'buscar_alumnos.html', context)



def normalizar_texto(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower()


def ContarFaltas(lista_id):
    curso_academico_actual = get_current_academic_year()

    contar = []
    for alum in lista_id:
        am = str(len(Amonestaciones.objects.filter(IdAlumno_id=list(alum.values())[0],
                                                   curso_academico=curso_academico_actual)))
        sa = str(
            len(Sanciones.objects.filter(IdAlumno_id=list(alum.values())[0], curso_academico=curso_academico_actual)))

        contar.append(am + "/" + sa)
    return contar


def ContarFaltasHistorico(lista_id):
    contar = []
    for alum in lista_id:
        am = str(len(Amonestaciones.objects.filter(IdAlumno_id=list(alum.values())[0])))
        sa = str(len(Sanciones.objects.filter(IdAlumno_id=list(alum.values())[0])))

        contar.append(am + "/" + sa)
    return contar


def _is_yes(value: str) -> bool:
    """Devuelve True si la cadena indica afirmación (sí/si/yes/1/x), ignorando tildes y BOM."""
    if value is None:
        return False
    s = str(value).strip().lstrip('\ufeff').lower()
    # normalizaciones típicas
    s = s.replace('í', 'i')  # sí -> si
    return s in {'si', 'sí', 'yes', 'y', '1', 'true', 'x'}



@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def importar_materias(request: HttpRequest):
    niveles = Niveles.objects.all()
    curso_academico = get_current_academic_year()

    if request.method == "POST":
        total_creadas_global = 0

        for nivel in niveles:
            file_key = f'csv_nivel_{nivel.id}'
            csv_file = request.FILES.get(file_key)
            if not csv_file:
                continue  # No se ha subido archivo para este nivel

            try:
                csv_reader = decode_file(csv_file)  # <- tu helper existente (devuelve iterador CSV)
            except UnicodeDecodeError:
                messages.error(request, f"No se pudo leer el archivo para {nivel.Nombre}. Usa codificación UTF-8.")
                continue

            # Saltar cabecera (por si acaso con BOM)
            header = next(csv_reader, None)

            creadas_nivel = 0
            procesadas_nivel = 0

            with transaction.atomic():
                for row in csv_reader:
                    # Esperamos al menos 5 columnas según el CSV mostrado:
                    # 0: ¿Se imparte en el centro?
                    # 1: Materia
                    # 2: Grupo de materias (ignorado)
                    # 3: Abreviatura
                    # 4: Número de créditos
                    if len(row) < 5:
                        continue

                    impartida = _is_yes(row[0])
                    if not impartida:
                        continue  # ignorar materias no impartidas

                    nombre = (row[1] or "").strip().lstrip('\ufeff')
                    abrev = (row[3] or "").strip()
                    creditos = (row[4] or "").strip()

                    # Horas a partir del número de créditos (si viene numérico)
                    try:
                        horas = int(creditos)
                    except (TypeError, ValueError):
                        horas = 0

                    if not nombre:
                        continue  # fila inválida sin nombre

                    procesadas_nivel += 1

                    # Crea/actualiza por (nombre, nivel, curso_academico)
                    obj, created = Materia.objects.update_or_create(
                        nombre=nombre,
                        nivel=nivel,
                        curso_academico=curso_academico,
                        defaults={
                            'abr': abrev,
                            'horas': horas,
                        }
                    )
                    if created:
                        creadas_nivel += 1

            messages.success(
                request,
                f"{nivel.Nombre}: procesadas {procesadas_nivel} impartidas, creadas {creadas_nivel}."
            )
            total_creadas_global += creadas_nivel

        if total_creadas_global == 0:
            messages.info(
                request,
                f"No se crearon materias nuevas en el curso {curso_academico}. "
                f"Comprueba que el CSV tenga 'Sí' en la primera columna y que el curso actual sea el correcto."
            )

        return redirect('importar_materias')

    return render(request, "importar_materias.html", {"niveles": niveles})


def decode_file_dict(file):
    """Intenta decodificar el archivo con varias codificaciones comunes."""
    content = file.read()  # Leer todo el archivo como bytes
    for encoding in ['utf-8-sig', 'utf-8', 'latin1']:
        try:
            decoded = content.decode(encoding).splitlines()
            return csv.DictReader(decoded)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("No se pudo leer el archivo con ninguna codificación válida.")


def decode_file(file):
    """Intenta decodificar el archivo con varias codificaciones comunes."""
    content = file.read()  # Leer todo el archivo como bytes
    for encoding in ['utf-8-sig', 'utf-8', 'latin1']:
        try:
            decoded = content.decode(encoding).splitlines()
            return csv.reader(decoded)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("No se pudo leer el archivo con ninguna codificación válida.")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def importar_materias_impartidas(request):
    if request.method == 'POST' and 'csv_materias_impartidas' in request.FILES:
        csv_file = request.FILES['csv_materias_impartidas']

        curso_academico_actual = get_current_academic_year()

        try:
            csv_reader = decode_file_dict(csv_file)
        except UnicodeDecodeError:
            messages.error(request, f"No se pudo leer el archivo.")
            return redirect('importar_materias_impartidas')

        # Ignorar encabezado
        next(csv_reader, None)

        for row in csv_reader:
            nombre_nivel = row["Curso"].strip()
            nombre_materia = row["Materia"].strip()
            nombre_unidad = row["Unidad"].strip()
            nombre_profesor = row["Profesor/a"].strip()

            # Buscar Nivel
            nivel = Niveles.objects.filter(Nombre__iexact=nombre_nivel).first()
            if not nivel:
                messages.warning(request, f"Nivel no encontrado: {nombre_nivel}")
                continue

            # Buscar Curso (Unidad)
            curso = Cursos.objects.filter(Curso=nombre_unidad).first()
            if not curso:
                messages.warning(request, f"Curso (Unidad) no encontrado: {nombre_unidad} en {nombre_nivel}")
                continue

            # Buscar Materia
            materia = Materia.objects.filter(nombre=nombre_materia, nivel=nivel, curso_academico=curso_academico_actual).first()
            if not materia:
                messages.warning(request, f"Materia no encontrada: {nombre_materia} en {nivel.Nombre}")
                continue

            # Buscar Profesor
            try:
                apellidos, nombre = [p.strip() for p in nombre_profesor.split(',', 1)]
                nombre_completo_csv = f"{apellidos}, {nombre}"
                normalizado_csv = quitar_tildes(nombre_completo_csv).lower()

                profesor = None
                for prof in Profesores.objects.filter(Baja=False):
                    nombre_prof = quitar_tildes(str(prof)).lower()
                    if nombre_prof == normalizado_csv:
                        profesor = prof
                        break

                if not profesor:
                    messages.warning(request, f"Profesor no encontrado: {nombre_profesor}")
                    continue
            except (ValueError, Profesores.DoesNotExist):
                messages.warning(request, f"Profesor no encontrado: {nombre_profesor}")
                continue

            # Crear MateriaImpartida
            obj, created = MateriaImpartida.objects.get_or_create(
                materia=materia,
                curso=curso,
                profesor=profesor,
                curso_academico=curso_academico_actual
            )
            if created:
                messages.success(request, f"Importada: {materia.nombre} en {curso.Curso} por {profesor}")
            else:
                messages.info(request, f"Ya existía: {materia.nombre} en {curso.Curso} por {profesor}")

        return redirect('importar_materias_impartidas')

    return render(request, 'importar_materias_impartidas.html')


def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def importar_matriculas_materias(request):
    if request.method == "POST" and 'csv_matriculas' in request.FILES:


        csv_file = request.FILES['csv_matriculas']

        try:
            csv_reader = decode_file(csv_file)
        except UnicodeDecodeError:
            messages.error(request, "No se pudo leer el archivo.")
            return redirect('importar_matriculas_materias')

        encabezado = next(csv_reader)
        materias_csv = encabezado[2:]

        nuevas = []
        existentes = []
        errores = []
        multi_profesores = 0

        curso_academico_actual = get_current_academic_year()

        cursos_del_nivel = Cursos.objects.all()
        if not cursos_del_nivel.exists():
            messages.error(request, f"No se encontraron cursos")
            return redirect('importar_matriculas_materias')

        for row_index, row in enumerate(csv_reader, start=2):  # Desde fila 2 por encabezado
            nombre_alumno_csv = quitar_tildes(row[0]).strip().lower()
            nombre_unidad_csv = quitar_tildes(row[1]).strip().lower()

            try:

                curso = cursos_del_nivel.get(Curso__iexact=row[1].strip())
            except Cursos.DoesNotExist:
                errores.append(f"Fila {row_index}: Unidad no encontrada - {row[1]}")
                continue

            alumnos_en_curso = Alumnos.objects.filter(Unidad=curso)
            alumno = next(
                (a for a in alumnos_en_curso if quitar_tildes(a.Nombre).strip().lower() == nombre_alumno_csv),
                None
            )

            if not alumno:
                errores.append(f"Fila {row_index}: Alumno no encontrado - {row[0]}")
                continue

            for i, valor in enumerate(row[2:]):
                if valor.strip().upper() != "MATR":
                    continue

                nombre_materia_csv = quitar_tildes(materias_csv[i]).strip().lower()

                materias_imp = MateriaImpartida.objects.filter(
                    curso=curso,
                    materia__nombre__iexact=materias_csv[i].strip(),
                    curso_academico=curso_academico_actual
                )

                if not materias_imp.exists():
                    errores.append(f"Fila {row_index}: Materia '{materias_csv[i]}' no encontrada en {curso.Curso}")
                    continue

                if materias_imp.count() > 1:
                    multi_profesores += 1

                for materia_imp in materias_imp:
                    matricula, creada = MatriculaMateria.objects.get_or_create(
                        alumno=alumno,
                        materia_impartida=materia_imp,
                        curso_academico = curso_academico_actual
                    )

                    if creada:
                        nuevas.append(
                            f"{alumno.Nombre} → {materia_imp.materia.nombre} ({curso.Curso}) [{materia_imp.profesor}]")
                    else:
                        existentes.append(
                            f"{alumno.Nombre} ya estaba en {materia_imp.materia.nombre} ({curso.Curso}) [{materia_imp.profesor}]")

        resumen = {
            'nuevas': nuevas,
            'existentes': existentes,
            'errores': errores,
            'multi_profesores': multi_profesores
        }

        return render(request, 'importar_matriculas_materias.html', {'resumen': resumen})

    return render(request, 'importar_matriculas_materias.html')


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def ver_matriculas(request):
    cursos = Cursos.objects.all()
    cursosacademicos = CursoAcademico.objects.all().order_by("nombre")
    datos = []
    curso_seleccionado = None
    cursoacademico_seleccionado = None
    curso_academico_actual = get_current_academic_year()

    if request.method == "POST":
        curso_id = request.POST.get("curso")
        cursoacademico_id = request.POST.get('CursoAcademico')
        if curso_id and cursoacademico_id:
            curso_seleccionado = Cursos.objects.get(id=curso_id)
            cursoacademico_seleccionado = CursoAcademico.objects.get(id=cursoacademico_id)
            alumnos = curso_seleccionado.alumnos_set.all().order_by("Nombre")

            for alumno in alumnos:
                matriculas = MatriculaMateria.objects.filter(alumno=alumno, curso_academico=cursoacademico_id)
                materias_agrupadas = {}

                for mat in matriculas:
                    nombre_materia = mat.materia_impartida.materia.nombre
                    profesor = str(mat.materia_impartida.profesor)

                    if nombre_materia not in materias_agrupadas:
                        materias_agrupadas[nombre_materia] = set()
                    materias_agrupadas[nombre_materia].add(profesor)

                # Convertir sets a listas para que sean iterables en la template
                materias_agrupadas = {
                    materia: sorted(list(profesores))
                    for materia, profesores in materias_agrupadas.items()
                }

                datos.append({
                    "alumno": alumno,
                    "materias_agrupadas": materias_agrupadas
                })

    return render(request, "ver_matriculas.html", {
        "cursos": cursos,
        "curso_seleccionado": curso_seleccionado,
        "cursoacademico_seleccionado": cursoacademico_seleccionado,
        "cursosacademicos": cursosacademicos,
        "datos": datos
    })


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def listar_materias_impartidas(request):
    cursos_disponibles = Cursos.objects.all()
    curso_id = request.GET.get('curso')
    cursoacademico_id = request.GET.get('CursoAcademico')
    registros = MateriaImpartida.objects.select_related('materia', 'curso', 'profesor')
    cursos_academicos = CursoAcademico.objects.order_by('nombre')

    cursoacademico_seleccionado = None

    if curso_id and cursoacademico_id:
        registros = registros.filter(curso_id=curso_id, curso_academico_id=cursoacademico_id)
        cursoacademico_seleccionado = CursoAcademico.objects.get(id=cursoacademico_id)

    materias_agrupadas = []

    agrupados = defaultdict(list)
    for reg in registros:
        clave = (reg.curso, reg.materia)
        agrupados[clave].append(reg.profesor)

    for (curso, materia), profesores in agrupados.items():
        materias_agrupadas.append({
            'curso': curso,
            'materia': materia,
            'profesores': profesores
        })

    context = {
        'materias_agrupadas': materias_agrupadas,
        'cursos_disponibles': cursos_disponibles,
        'curso_seleccionado': int(curso_id) if curso_id else None,
        'cursosacademicos': cursos_academicos,
        'cursoacademico_seleccionado': cursoacademico_seleccionado
    }
    return render(request, 'listar_materias_impartidas.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def importar_libros_texto(request):
    if request.method == "POST" and 'csv_libros' in request.FILES:
        nivel_id = request.POST.get('nivel')
        if not nivel_id:
            messages.error(request, "Debes seleccionar un nivel.")
            return redirect('importar_libros_texto')

        csv_file = request.FILES['csv_libros']

        curso_actual = get_current_academic_year()

        try:
            csv_reader = decode_file(csv_file)
        except UnicodeDecodeError:
            messages.error(request, "No se pudo leer el archivo.")
            return redirect('importar_libros_texto')

        try:
            nivel = Niveles.objects.get(id=nivel_id)
        except Niveles.DoesNotExist:
            messages.error(request, "Nivel no encontrado.")
            return redirect('importar_libros_texto')

        encabezado = next(csv_reader)
        nuevas = []
        errores = []

        materias_nivel = Materia.objects.filter(nivel=nivel, curso_academico=curso_actual)

        for row_index, row in enumerate(csv_reader, start=2):
            nombre_materia_csv = quitar_tildes(row[0]).strip().lower()
            if not nombre_materia_csv:
                continue

            materia = next(
                (m for m in materias_nivel if quitar_tildes(m.nombre).strip().lower() == nombre_materia_csv),
                None
            )

            if not materia:
                errores.append(f"Fila {row_index}: Materia no encontrada - {row[0]}")
                continue

            titulo = row[3].strip()
            if not titulo:
                continue  # Saltar libros sin título

            libro = LibroTexto(
                materia=materia,
                nivel=nivel,
                isbn=row[1].strip(),
                editorial=row[2].strip(),
                titulo=titulo,
                anyo_implantacion=int(row[4]) if row[4].isdigit() else None,
                importe_estimado=float(row[5].replace(',', '.')) if row[5].replace(',', '.').replace('.', '',
                                                                                                     1).isdigit() else None,
                es_digital=row[6].strip().lower() == "sí",
                incluir_en_cheque_libro=row[7].strip().lower() == "sí",
                es_otro_material=row[8].strip().lower() == "sí",
                curso_academico = curso_actual
            )
            libro.save()
            nuevas.append(f"{materia.nombre} - {libro.titulo or 'Sin título'}")

        return render(request, 'importar_libros_texto.html', {
            'resumen': {
                'nuevos': nuevas,
                'errores': errores,
            },
            'niveles': Niveles.objects.all()
        })

    return render(request, 'importar_libros_texto.html', {
        'niveles': Niveles.objects.all()
    })


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def ver_libros_texto(request):
    niveles = Niveles.objects.all()
    libros = []

    nivel_id = request.GET.get('Nivel')
    cursoacademico_id = request.GET.get('CursoAcademico')
    nivel_seleccionado = None
    cursoacademico_seleccionado = None

    cursos_academicos = CursoAcademico.objects.order_by('nombre')

    if nivel_id and cursoacademico_id:
        try:
            nivel_seleccionado = Niveles.objects.get(id=nivel_id)
            cursoacademico_seleccionado = CursoAcademico.objects.get(id=cursoacademico_id)
            libros = LibroTexto.objects.filter(nivel=nivel_seleccionado,
                                               curso_academico=cursoacademico_seleccionado).select_related(
                'materia').order_by('materia__nombre')
        except Niveles.DoesNotExist or CursoAcademico.DoesNotExist:
            nivel_seleccionado = None
            cursoacademico_seleccionado = None

    return render(request, 'ver_libros_texto.html', {
        'niveles': niveles,
        'libros': libros,
        'nivel_seleccionado': nivel_seleccionado,
        'cursoacademico_seleccionado': cursoacademico_seleccionado,
        'cursosacademicos': cursos_academicos
    })


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def seleccionar_revision_view(request):
    profesores_qs = Profesores.objects.filter(Baja=False)

    form = SeleccionRevisionForm(
        request.POST or None,
        profesores_qs=profesores_qs,
        materias_qs=Materia.objects.none(),
        libros_qs=LibroTexto.objects.none()
    )

    return render(request, 'seleccion_revision.html', {
        'form': form,
        'momentos': MomentoRevisionLibros.objects.all()
    })


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def revisar_libros(request):
    profesor = request.user.profesor

    form = SeleccionRevisionProfeForm(
        request.POST or None,
        profesor=profesor,
        materias_qs=Materia.objects.none(),
        libros_qs=LibroTexto.objects.none()
    )

    return render(request, 'revisar_libros.html', {
        'form': form,
        'profesor': profesor,
        'momentos': MomentoRevisionLibros.objects.all()
    })


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def revisar_libros_view(request, profesor_id, momento_id, materia_id, libro_id):
    profesor = get_object_or_404(Profesores, pk=profesor_id)
    momento = get_object_or_404(MomentoRevisionLibros, pk=momento_id)
    materia = get_object_or_404(Materia, pk=materia_id)
    libro = get_object_or_404(LibroTexto, pk=libro_id)
    curso_academico_actual = get_current_academic_year()

    # Buscar las materias impartidas por ese profesor de esa materia
    materias_impartidas = MateriaImpartida.objects.filter(
        profesor=profesor,
        materia=materia,
        curso_academico = curso_academico_actual
    )

    # Buscar los alumnos matriculados en esas materias impartidas
    matriculas = MatriculaMateria.objects.filter(
        materia_impartida__in=materias_impartidas,
        curso_academico = curso_academico_actual
    ).select_related('alumno')

    alumnos = [m.alumno for m in matriculas]

    return render(request, 'revision_libros.html', {
        'profesor': profesor,
        'momento': momento,
        'materia': materia,
        'libro': libro,
        'alumnos': alumnos,
    })


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def revision_exitosa_view(request):
    return render(request, 'revision_exitosa.html')


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def obtener_materias_ajax(request):
    profesor_id = request.GET.get('profesor_id')
    materias = Materia.objects.filter(materiaimpartida__profesor_id=profesor_id).distinct()
    data = [{'id': m.id, 'nombre': str(m)} for m in materias]
    return JsonResponse(data, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def obtener_libros_ajax(request):
    materia_id = request.GET.get('materia_id')
    libros = LibroTexto.objects.filter(materia_id=materia_id)
    data = [{'id': l.id, 'nombre': str(l)} for l in libros]
    return JsonResponse(data, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def get_cursos_profesor(request):
    curso_academico_actual = get_current_academic_year()
    profesor_id = request.GET.get('profesor_id')
    cursos = Cursos.objects.filter(materiaimpartida__profesor_id=profesor_id, materiaimpartida__curso_academico=curso_academico_actual).distinct()
    data = [{'id': curso.id, 'nombre': str(curso)} for curso in cursos]
    return JsonResponse(data, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def get_materias_profesor_curso(request):
    curso_academico_actual = get_current_academic_year()
    profesor_id = request.GET.get('profesor_id')
    curso_id = request.GET.get('curso_id')
    materias = Materia.objects.filter(materiaimpartida__profesor_id=profesor_id,
                                      materiaimpartida__curso_id=curso_id,
                                      materiaimpartida__curso_academico=curso_academico_actual).distinct()
    data = [{'id': m.id, 'nombre': str(m)} for m in materias]
    return JsonResponse(data, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def get_libros_materia(request):
    curso_academico_actual = get_current_academic_year()
    materia_id = request.GET.get('materia_id')
    libros = LibroTexto.objects.filter(materia_id=materia_id)
    data = [{'id': l.id, 'titulo': l.titulo} for l in libros]
    return JsonResponse(data, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def revision_libros(request, profesor_id, momento_id, materia_id, libro_id):

    curso_academico_actual = get_current_academic_year()
    # Obtener MateriaImpartida concreta
    materia_impartida = MateriaImpartida.objects.filter(
        profesor_id=profesor_id,
        materia_id=materia_id,
        curso_academico = curso_academico_actual
    ).first()

    if not materia_impartida:
        return render(request, 'error.html', {'mensaje': 'No se ha encontrado la materia impartida.'})

    # Obtener alumnos matriculados
    matriculas = MatriculaMateria.objects.filter(materia_impartida=materia_impartida, curso_academico=curso_academico_actual).select_related('alumno')

    momento = get_object_or_404(MomentoRevisionLibros, pk=momento_id)
    libro = get_object_or_404(LibroTexto, pk=libro_id)
    profesor = get_object_or_404(Profesores, pk=profesor_id)

    contexto = {
        'materia_impartida': materia_impartida,
        'alumnos': [m.alumno for m in matriculas],
        'libro': libro,
        'momento': momento,
        'profesor': profesor,
    }

    return render(request, 'revision_libros.html', contexto)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def get_tabla_revision(request):
    profesor_id = request.GET.get('profesor_id')
    curso_id = request.GET.get('curso_id')
    materia_id = request.GET.get('materia_id')
    libro_id = request.GET.get('libro_id')
    momento_id = request.GET.get('momento_id')

    curso_academico_actual = get_current_academic_year()

    if not all([profesor_id, curso_id, materia_id, libro_id, momento_id]):
        return JsonResponse({'error': 'Faltan datos'}, status=400)

    # Obtener instancias base
    profesor = Profesores.objects.get(pk=profesor_id)
    materia = Materia.objects.get(pk=materia_id)
    curso = Cursos.objects.get(pk=curso_id)
    libro = LibroTexto.objects.get(pk=libro_id)
    momento = MomentoRevisionLibros.objects.get(pk=momento_id)

    # Buscar la MateriaImpartida concreta
    try:
        materia_impartida = MateriaImpartida.objects.get(
            profesor=profesor,
            materia=materia,
            curso=curso,
            curso_academico = curso_academico_actual
        )
    except MateriaImpartida.DoesNotExist:
        return JsonResponse({'error': 'No se encontró la asignación de esa materia con ese profesor en ese curso.'},
                            status=404)

    # Buscar alumnos matriculados en esa materia impartida
    alumnos = MatriculaMateria.objects.filter(
        materia_impartida=materia_impartida,
        curso_academico = curso_academico_actual
    ).select_related('alumno').order_by('alumno__Nombre')

    estados = momento.estados.all().order_by('orden')

    return render(request, 'includes/tabla_revision_libros.html', {
        'alumnos': [m.alumno for m in alumnos],
        'estados': estados,
        'profesor': profesor,
        'materia': materia,
        'libro': libro,
        'momento': momento,
    })


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def guardar_revision_libros(request):
    if request.method == 'POST':
        profesor_id = request.POST.get('profesor')

        if not profesor_id:
            profesor_id = request.user.profesor.id

        curso_id = request.POST.get('curso')
        materia_id = request.POST.get('materia')
        libro_id = request.POST.get('libro')
        momento_id = request.POST.get('momento')

        if not all([profesor_id, curso_id, materia_id, libro_id, momento_id]):
            messages.error(request, "Faltan datos en el formulario.")
            return redirect('revision_libros_inicio')

        profesor = get_object_or_404(Profesores, pk=profesor_id)
        curso = get_object_or_404(Cursos, pk=curso_id)
        materia = get_object_or_404(Materia, pk=materia_id)
        libro = get_object_or_404(LibroTexto, pk=libro_id)
        momento = get_object_or_404(MomentoRevisionLibros, pk=momento_id)

        revision_id = request.POST.get('revision_id')
        if revision_id:
            revision = get_object_or_404(RevisionLibro, id=revision_id)
        else:
            # Crear o recuperar la revisión general
            fecha_hoy = now().date()
            revision, created = RevisionLibro.objects.get_or_create(
                profesor=profesor,
                curso=curso,
                materia=materia,
                libro=libro,
                momento=momento,
                fecha=fecha_hoy,
            )

        # Recoger los datos por alumno
        alumnos_ids = [
            key.split('_')[1] for key in request.POST.keys() if key.startswith('estado_')
        ]

        for alumno_id in alumnos_ids:
            estado_id = request.POST.get(f'estado_{alumno_id}')
            observaciones = request.POST.get(f'observaciones_{alumno_id}', '').strip()

            if not estado_id:
                continue  # Saltar si no se indicó estado

            alumno = get_object_or_404(Alumnos, pk=alumno_id)
            estado = get_object_or_404(EstadoLibro, pk=estado_id)

            # Crear o actualizar la revisión individual
            RevisionLibroAlumno.objects.update_or_create(
                revision=revision,
                alumno=alumno,
                defaults={
                    'estado': estado,
                    'observaciones': observaciones,
                }
            )

        messages.success(request, "Revisión guardada correctamente.")
        return redirect('revision_libros_inicio')

    return redirect('revision_libros_inicio')


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def resumen_revisiones(request):
    revisiones = RevisionLibro.objects.select_related(
        'profesor', 'materia', 'libro', 'momento', 'curso_academico'
    ).prefetch_related('detalles__alumno')

    resumen = []

    for r in revisiones:
        alumnos_revisados = r.detalles.values_list('alumno_id', flat=True).distinct().count()

        total_matriculados = MatriculaMateria.objects.filter(
            materia_impartida__materia=r.materia,
            materia_impartida__profesor=r.profesor,
            materia_impartida__curso=r.curso,
            materia_impartida__curso_academico = r.curso_academico
        ).values('alumno_id').distinct().count()

        resumen.append({
            'id': r.id,
            'profesor': r.profesor,
            'curso': r.curso,
            'materia': r.materia,
            'libro': r.libro,
            'momento': r.momento,
            'curso_academico': r.curso_academico,
            'fecha': r.fecha,
            'revisados': alumnos_revisados,
            'matriculados': total_matriculados,
        })

    resumen.sort(key=lambda r: r['fecha'], reverse=True)

    profesores = sorted(set(str(r['profesor']) for r in resumen))
    cursos = sorted(set(str(r['curso']) for r in resumen))
    materias = sorted(set(str(r['materia']) for r in resumen))
    libros = sorted(set(str(r['libro']) for r in resumen))
    momentos = sorted(set(str(r['momento']) for r in resumen))
    cursosacademicos = sorted(set(str(r['curso_academico']) for r in resumen))

    context = {
        'resumen': resumen,
        'profesores': profesores,
        'cursos': cursos,
        'materias': materias,
        'libros': libros,
        'momentos': momentos,
        'cursosacademicos': cursosacademicos,
    }

    return render(request, 'resumen_revisiones.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def detalle_revision(request, revision_id):
    revision = get_object_or_404(
        RevisionLibro.objects.select_related(
            'profesor', 'materia', 'libro', 'momento', 'curso_academico'
        ).prefetch_related('detalles__alumno', 'detalles__estado'),
        pk=revision_id
    )

    return render(request, 'detalle_revision.html', {
        'revisiones': revision.detalles.all(),
        'profesor': revision.profesor,
        'curso': revision.curso,
        'materia': revision.materia,
        'libro': revision.libro,
        'momento': revision.momento,
        'curso_academico': revision.curso_academico,
        'fecha': revision.fecha
    })


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def mis_revisiones(request):
    profesor = request.user.profesor
    curso_academico_actual = get_current_academic_year()
    cursos_anteriores = get_previous_academic_years()

    revisiones = RevisionLibro.objects.filter(profesor=profesor).select_related(
        'profesor', 'materia', 'libro', 'momento', 'curso_academico'
    ).prefetch_related('detalles__alumno')

    resumen_actual = []
    resumen_anteriores = {}  # Claves: curso_id

    for r in revisiones:
        alumnos_revisados = r.detalles.values_list('alumno_id', flat=True).distinct().count()

        total_matriculados = MatriculaMateria.objects.filter(
            materia_impartida__materia=r.materia,
            materia_impartida__profesor=r.profesor,
            materia_impartida__curso=r.curso,
            materia_impartida__curso_academico=r.curso_academico
        ).values('alumno_id').distinct().count()

        resumen_item = {
            'id': r.id,
            'profesor': r.profesor,
            'curso': r.curso,
            'materia': r.materia,
            'libro': r.libro,
            'momento': r.momento,
            'curso_academico': r.curso_academico,
            'fecha': r.fecha,
            'revisados': alumnos_revisados,
            'matriculados': total_matriculados,
        }

        if r.curso_academico == curso_academico_actual:
            resumen_actual.append(resumen_item)
        elif r.curso_academico.id in [c.id for c in cursos_anteriores]:
            curso_id = r.curso_academico.id
            if curso_id not in resumen_anteriores:
                resumen_anteriores[curso_id] = {
                    'curso': r.curso_academico,
                    'revisiones': []
                }
            resumen_anteriores[curso_id]['revisiones'].append(resumen_item)

    resumen_actual.sort(key=lambda r: r['fecha'], reverse=True)
    for info in resumen_anteriores.values():
        info['revisiones'].sort(key=lambda r: r['fecha'], reverse=True)

    # Construir lista ordenada según cursos_anteriores
    resumen_anteriores_ordenado = []
    for curso in cursos_anteriores:
        curso_id = curso.id
        if curso_id in resumen_anteriores:
            resumen_anteriores_ordenado.append((curso, resumen_anteriores[curso_id]['revisiones']))

    context = {
        'resumen': resumen_actual,
        'resumen_anteriores': resumen_anteriores_ordenado,
    }

    return render(request, 'mis_revisiones.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def editar_revision_libros(request, revision_id):
    revision = get_object_or_404(RevisionLibro, id=revision_id)
    estados = revision.momento.estados.all().order_by('orden')


    # Obtener la materia impartida desde los datos de la revisión
    try:
        materia_impartida = MateriaImpartida.objects.get(
            profesor=revision.profesor,
            curso=revision.curso,
            materia=revision.materia
        )
    except MateriaImpartida.DoesNotExist:
        materia_impartida = None

    # Obtener todos los alumnos matriculados en esa materia
    alumnos = []
    if materia_impartida:
        matriculas = MatriculaMateria.objects.filter(
            materia_impartida=materia_impartida
        ).select_related('alumno').order_by('alumno__Nombre')
        alumnos = [m.alumno for m in matriculas]

    # Generar lista con revisiones existentes o "vacías"
    alumnos_revisionados = []
    for alumno in alumnos:
        rev_alumno = RevisionLibroAlumno.objects.filter(
            revision=revision, alumno=alumno
        ).first()
        if not rev_alumno:
            # Crear objeto temporal (no guardado en DB)
            rev_alumno = RevisionLibroAlumno(
                revision=revision,
                alumno=alumno,
                estado=None,
                observaciones=''
            )
        alumnos_revisionados.append(rev_alumno)

    return render(request, 'editar_revision.html', {
        'revision': revision,
        'estados': estados,
        'alumnos_revisionados': alumnos_revisionados,
    })

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def morosos_view(request):
    niveles_deseados = ["1º ESO"]
    curso_actual = get_current_academic_year()

    alumnos = Alumnos.objects.filter(Unidad__Nivel__Abr__in=niveles_deseados).select_related('Unidad__Nivel')
    alumnos_morosos = []

    for alumno in alumnos:
        # Set para evitar procesar una misma materia varias veces
        materias_procesadas = set()
        materias_faltantes = []
        titulos_faltantes = []

        matriculas = MatriculaMateria.objects.filter(
            alumno=alumno,
            curso_academico=curso_actual
        ).select_related('materia_impartida__materia')

        for matricula in matriculas:
            materia = matricula.materia_impartida.materia

            if materia.id in materias_procesadas:
                continue  # ya procesada

            materias_procesadas.add(materia.id)

            nivel = alumno.Unidad.Nivel

            libros_materia = LibroTexto.objects.filter(
                materia=materia,
                nivel=nivel,
                curso_academico=curso_actual
            )

            if not libros_materia.exists():
                continue

            # Verificamos si el alumno ha devuelto al menos uno de los libros de esta materia
            alguna_revision = RevisionLibroAlumno.objects.filter(
                alumno=alumno,
                revision__materia=materia,
                revision__curso=alumno.Unidad,
                revision__curso_academico=curso_actual,
                revision__libro__in=libros_materia
            ).exists()

            if not alguna_revision:
                materias_faltantes.append(materia.nombre)
                titulos_comb = " / ".join(
                    sorted(set(libro.titulo or "Sin título" for libro in libros_materia))
                )
                titulos_faltantes.append(titulos_comb)

        if materias_faltantes:
            alumnos_morosos.append({
                'alumno': alumno.Nombre,
                'alumnoObject': alumno,
                'unidad': alumno.Unidad.Curso,
                'num_faltan': len(materias_faltantes),
                'materias': sorted(materias_faltantes),
                'titulos': sorted(titulos_faltantes),
            })

    alumnos_morosos.sort(key=lambda x: x['unidad'])

    context = {'morosos': alumnos_morosos}
    return render(request, 'morosos.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def destrozones_view(request):
    curso_actual = get_current_academic_year()

    estados_deteriorados = EstadoLibro.objects.filter(nombre__in=["Malo", "Necesita reposición"])
    niveles_objetivo = Niveles.objects.filter(Abr__in=["3º ESO"])
    print(niveles_objetivo)

    alumnos_revisionados = RevisionLibroAlumno.objects.filter(
        revision__curso_academico=curso_actual,
        estado__in=estados_deteriorados
    ).select_related('alumno', 'revision__curso', 'revision__libro', 'revision__materia')

    resultado = {}
    for rla in alumnos_revisionados:
        alumno = rla.alumno
        unidad = alumno.Unidad
        if not unidad or not unidad.Nivel or unidad.Nivel not in niveles_objetivo:
            print("continuamos: "+unidad.Nivel.Abr)
            continue

        key = alumno.id
        if key not in resultado:
            resultado[key] = {
                'alumno': alumno.Nombre,
                'unidad': unidad.Curso,
                'libros_danados': set(),
                'materias': set(),
                'titulos': set(),
            }

        resultado[key]['libros_danados'].add(rla.revision.libro)
        resultado[key]['materias'].add(rla.revision.materia.nombre)
        resultado[key]['titulos'].add(rla.revision.libro.titulo or "Sin título")

    lista_final = sorted([
        {
            'alumno': datos['alumno'],
            'unidad': datos['unidad'],
            'num_danados': len(datos['libros_danados']),
            'materias': sorted(datos['materias']),
            'titulos': sorted(datos['titulos']),
        }
        for datos in resultado.values()
    ], key=lambda x: x['unidad'])

    return render(request, 'destrozones.html', {
        'datos': lista_final,
    })


def pruebacal(request):
    context = {
        'horas_antes_recreo': range(1, 4),
        'horas_despues_recreo': range(4, 7),
    }
    return render(request, 'mi_preferencia_horaria.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def mi_preferencia_horaria(request):
    profesor = request.user.profesor
    preferencia, created = PreferenciaHorario.objects.get_or_create(profesor=profesor)

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    if request.method == 'POST':
        # Recuperamos datos del POST
        horario = json.loads(request.POST.get('horario_json'))
        flex_inicio = request.POST.get('flex_inicio') == 'true'
        flex_fin = request.POST.get('flex_fin') == 'true'
        guardias = json.loads(request.POST.get('guardias_json'))
        observaciones = request.POST.get('observaciones', '')

        # Guardamos
        preferencia.horario = horario
        preferencia.flexibilidad_inicio = flex_inicio
        preferencia.flexibilidad_fin = flex_fin
        preferencia.guardias = guardias
        preferencia.observaciones = observaciones
        preferencia.save()

        return redirect('mi_preferencia_horaria')  # o alguna vista de confirmación


    guardias = preferencia.guardias if preferencia.guardias else []
    # Filtrar valores nulos por si acaso
    guardias = [g for g in guardias if g is not None]

    return render(request, 'mi_preferencia_horaria.html', {
        'preferencia': preferencia,
        'dias': dias,
        'horas_antes_recreo': range(1, 4),
        'horas_despues_recreo': range(4, 7),
        'horario_json': json.dumps(preferencia.horario),
        'guardias_json': json.dumps(guardias),
    })

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def preferencias_profesores(request):

    profesores = Profesores.objects.filter(Baja=False)
    preferencias = {p.profesor_id: p for p in PreferenciaHorario.objects.all()}

    # Procesar resumen horario para cada preferencia
    for pref in preferencias.values():
        pref.horario_resumen = procesar_horario(pref.horario)

    return render(request, 'listado_preferencias.html', {
        'profesores': profesores,
        'preferencias': preferencias
    })

def procesar_horario(horario):
    """Convierte claves como 'Lunes-2' con valor True en 'L-2º', etc."""
    map_dias = {
        'Lunes': 'L',
        'Martes': 'M',
        'Miércoles': 'X',
        'Jueves': 'J',
        'Viernes': 'V',
    }
    if not horario:
        return []
    resultado = []
    for clave, valor in horario.items():
        if not valor:
            continue
        partes = clave.split('-')
        if len(partes) != 2:
            continue
        dia, hora = partes
        inicial = map_dias.get(dia, dia[0].upper())
        resultado.append(f"{inicial}-{hora}º")
    return resultado


def copiar_horario(titular, sustituto):
    curso_academico_actual = get_current_academic_year()
    horarios = ItemHorario.objects.filter(profesor=titular, curso_academico=curso_academico_actual)
    for h in horarios:
        h.pk = None  # Clonar
        h.profesor = sustituto
        h.save()


def copiar_guardias(titular, sustituto):
    # Obtener todos los TiempoGuardia del titular (con sus respectivos ItemGuardia)
    tiempos_guardia_orig = TiempoGuardia.objects.filter(profesor=titular)

    for t in tiempos_guardia_orig:
        # Crear un TiempoGuardia nuevo para el sustituto, vinculado al mismo ItemGuardia
        TiempoGuardia.objects.create(
            profesor=sustituto,
            dia_semana=t.dia_semana,
            tramo=t.tramo,
            tiempo_asignado=t.tiempo_asignado,
            item_guardia=t.item_guardia,
            curso_academico=t.curso_academico,
        )

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def crear_sustituto(request):
    if request.method == 'POST':
        form = ProfesorSustitutoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            with transaction.atomic():  # Garantiza atomicidad y rollback si falla algo
                # Crear usuario
                user = User.objects.create(
                    username=data['username'],
                    email=data['email'],
                    password=make_password(data['dni']),  # DNI como contraseña
                )

                # Copiar grupos del usuario titular
                titular_user = data['profesor_sustituido'].user  # Usuario del profesor titular
                if titular_user:
                    grupos = titular_user.groups.all()
                    user.groups.set(grupos)  # Asignar todos los grupos al nuevo usuario

                # Crear Profesor sustituto
                profesor_sustituto = Profesores.objects.create(
                    user=user,
                    Nombre=data['nombre'],
                    Apellidos=data['apellidos'],
                    DNI=data['dni'],
                    Email=data['email'],
                    SustitutoDe=data['profesor_sustituido'],
                    Departamento=data['profesor_sustituido'].Departamento,
                    Baja=False,
                )

                titular = data['profesor_sustituido']

                # Actualizar cursos donde titular es tutor
                cursos_tutor = Cursos.all_objects.filter(Tutor=titular)
                for curso in cursos_tutor:
                    curso.Tutor = profesor_sustituto
                    curso.save()

                materias_impartidas = MateriaImpartida.objects.filter(profesor=titular)
                for mi in materias_impartidas:
                    mi.profesor = profesor_sustituto
                    mi.save()

                # Copiar horario y guardias
                copiar_horario(titular, profesor_sustituto)
                copiar_guardias(titular, profesor_sustituto)

                # Marcar titular como dado de baja
                titular.Baja = True
                titular.save()

            messages.success(request, "Profesor sustituto creado y datos sincronizados con tutorías actualizadas.")
            return redirect('lista_sustitutos')  # Cambiar al nombre real de la URL
    else:
        form = ProfesorSustitutoForm()

    return render(request, 'crear_sustituto.html', {'form': form})

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def lista_sustitutos(request):
    # Obtener todos los profesores que son sustitutos (tienen el campo SustitutoDe != None)
    sustitutos = Profesores.objects.filter(SustitutoDe__isnull=False, Baja=False).select_related('SustitutoDe').order_by('Apellidos')

    context = {
        'sustitutos': sustitutos,
    }
    return render(request, 'lista_sustitutos.html', context)


@require_POST
@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def reincorporar_titular(request):
    sustituto_id = request.POST.get('sustituto_id')
    titular_id = request.POST.get('titular_id')

    try:
        sustituto = Profesores.objects.get(id=sustituto_id)
        titular = Profesores.objects.get(id=titular_id)

        titular.Baja = False
        titular.save()

        sustituto.Baja = True
        sustituto.SustitutoDe = None
        sustituto.save()

        return JsonResponse({'success': True})

    except Profesores.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profesor no encontrado'})


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def buscar_revision_libro_olvidado(request):
    """Vista para localizar revisiones de libros entregados tarde (cursos anteriores)"""

    # Filtros iniciales
    alumno_seleccionado = None
    libro_seleccionado = None
    curso_academico_seleccionado = None

    # Búsqueda
    if request.method == 'POST':
        alumno_id = request.POST.get('alumno_id')
        libro_id = request.POST.get('libro_id')
        curso_academico_id = request.POST.get('curso_academico_id')

        if alumno_id:
            alumno_seleccionado = get_object_or_404(Alumnos, id=alumno_id)
        if libro_id:
            libro_seleccionado = get_object_or_404(LibroTexto, id=libro_id)
        if curso_academico_id:
            curso_academico_seleccionado = get_object_or_404(CursoAcademico, id=curso_academico_id)

    # Búsqueda inteligente de revisiones posibles
    revisiones_posibles = []

    if alumno_seleccionado and libro_seleccionado:
        # Estrategia 1: Búsqueda exacta (alumno + libro + curso)
        if curso_academico_seleccionado:
            revisiones_exactas = RevisionLibroAlumno.objects.filter(
                alumno=alumno_seleccionado,
                revision__libro=libro_seleccionado,
                revision__curso_academico=curso_academico_seleccionado
            ).select_related('revision__profesor', 'revision__materia',
                             'revision__libro', 'revision__momento', 'estado')

            revisiones_posibles.extend(revisiones_exactas)

        # Estrategia 2: Solo alumno + libro (todos los cursos)
        revisiones_libro = RevisionLibroAlumno.objects.filter(
            alumno=alumno_seleccionado,
            revision__libro=libro_seleccionado
        ).select_related('revision__profesor', 'revision__materia',
                         'revision__libro', 'revision__momento', 'estado').distinct()

        revisiones_posibles.extend(revisiones_libro)

    elif alumno_seleccionado:
        # Estrategia 3: Solo alumno (todos los libros)
        revisiones_alumno = RevisionLibroAlumno.objects.filter(
            alumno=alumno_seleccionado
        ).select_related('revision__profesor', 'revision__materia',
                         'revision__libro', 'revision__momento', 'estado')[:10]

        revisiones_posibles.extend(revisiones_alumno)

    # Agrupar por revisión única para evitar duplicados
    revisiones_unicas = {}
    for rev_alumno in revisiones_posibles:
        rev = rev_alumno.revision
        if rev.id not in revisiones_unicas:
            revisiones_unicas[rev.id] = {
                'revision': rev,
                'detalle_alumno': rev_alumno,
                'estado_actual': rev_alumno.estado,
                'observaciones': rev_alumno.observaciones,
            }

    # ALUMNOS ACTUALES (con unidad)
    alumnos_actuales = Alumnos.objects.filter(
        Unidad__isnull=False
    ).select_related('Unidad').order_by('Unidad__Curso', 'Nombre')

    # ALUMNOS ANTIGUOS (sin unidad)
    alumnos_antiguos = Alumnos.objects.filter(
        Unidad__isnull=True
    ).order_by('Nombre')

    libros = LibroTexto.objects.select_related(
        'materia',
        'nivel',
        'curso_academico'
    ).only(
               'id',
               'titulo',
               'materia',
               'nivel',
               'curso_academico',
               ).order_by(
        'curso_academico__nombre',
        'titulo'
    )
    context = {
        'alumno_seleccionado': alumno_seleccionado,
        'libro_seleccionado': libro_seleccionado,
        'curso_academico_seleccionado': curso_academico_seleccionado,
        'revisiones_posibles': list(revisiones_unicas.values()),
        'cursos_academicos': CursoAcademico.objects.all().order_by('-año_inicio'),
        'alumnos_antiguos': alumnos_antiguos,
        'alumnos_actuales': alumnos_actuales,

        'libros': libros,
        'unidades': Cursos.objects.all().order_by('Curso'),
    }


    return render(request, 'buscar_revision_olvidado.html', context)
