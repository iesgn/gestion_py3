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
import zipfile
import json
from io import TextIOWrapper

from centro.utils import get_nivel

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import render
from django.http import JsonResponse

from centro.models import Alumnos, InfoAlumnos, CursoAcademico, Centros, Niveles
from centro.utils import get_encoding
from analres.models import Calificaciones
from .forms import CargaCalificacionesSeneca, CargaRegAlumSeneca, CargaAdmisionSeneca


@staff_member_required
def calificaciones(request):
    if request.method == 'POST':
        form = CargaCalificacionesSeneca(request.POST, request.FILES)
        if form.is_valid():
            archivo_zip = form.cleaned_data['ArchivoZip']
            curso_academico = form.cleaned_data['CursoAcademico']
            convocatoria = form.cleaned_data['Convocatoria']

            try:
                data = {'nro_registros': 0, 'datos': []}
                with zipfile.ZipFile(archivo_zip) as zip_ref:
                    for nombre_archivo_csv in zip_ref.namelist():
                        if nombre_archivo_csv.endswith('.csv'):
                            with zip_ref.open(nombre_archivo_csv) as archivo_csv:
                                encoding = get_encoding(archivo_csv)
                                archivo_csv.seek(0)
                                csvfile = TextIOWrapper(archivo_csv, encoding=encoding)
                                reader = csv.DictReader(csvfile)
                                for row in reader:
                                    calificaciones_alumno = {}
                                    for key, value in row.items():
                                        try:
                                            calificaciones_alumno[key] = value
                                        except (ValueError, KeyError):
                                            print(f"Error processing row: {row}")  # Log error for debugging
                                            continue  # Skip invalid rows
                                    calificaciones_alumno['Curso Academico'] = curso_academico.nombre
                                    calificaciones_alumno['Convocatoria'] = convocatoria
                                    calificaciones_alumno['nombre_archivo'] = nombre_archivo_csv
                                    data['nro_registros'] += 1
                                    data['datos'].append(calificaciones_alumno)
                return JsonResponse(data)

            except Exception as e:
                print(f"Error procesando archivo Zip: {e}")  # Log the error for debugging
                return JsonResponse({'error': 'Ha ocurrido un error al procesar el archivo.'}, status=500)
    else:
        form = CargaCalificacionesSeneca()

    return render(request, 'cargar_calificaciones_seneca.html', {'form': form, 'menu_carga': True})

@staff_member_required
def calificaciones_procesar_datos(request):
    if request.method == 'POST':
        # Obtener los datos del cuerpo de la solicitud
        data = json.loads(request.body)

        curso_academico = CursoAcademico.objects.filter(nombre=data['Curso Academico']).first()
        if not curso_academico:
            return JsonResponse({'error': f'Curso Academico :{data["Curso Academico"]} no existe.'})

        alumno = Alumnos.objects.filter(Nombre=data['Alumno/a']).first()
        if not alumno:
            return JsonResponse({'error': f'El alumno :{data["Alumno/a"]} no existe.'})

        convocatoria = data['Convocatoria']
        nivel = get_nivel(data['nombre_archivo'])

        for key, val in data.items():
            if key not in ['Alumno/a', 'Unidad', 'Curso Academico', 'Convocatoria', 'nombre_archivo']:
                if val:
                    calif = val
                    error = False
                    try:
                        calif = str(int(val))
                    except ValueError:
                        error = True

                    try:
                        calif = str(int(float(val)))
                    except ValueError:
                        error = True

                    if not error:
                        calif = val

                    calificacion, creado = Calificaciones.objects.get_or_create(
                        curso_academico=curso_academico,
                        Nivel=nivel,
                        Alumno=alumno,
                        Convocatoria=convocatoria,
                        Materia=key,
                        defaults={
                            'Calificacion': calif,
                        }
                    )
                    if not creado:
                        calificacion.Calificacion = calif
                        calificacion.save()

        return JsonResponse({'status': 'success'})
    else:
        # Manejar otros métodos HTTP (si es necesario)
        return JsonResponse({'error': 'Método no permitido'})

@staff_member_required
def regalum(request):
    if request.method == 'POST':
        form = CargaRegAlumSeneca(request.POST, request.FILES)
        if form.is_valid():
            archivo_csv = form.cleaned_data['ArchivoCSV']
            curso_academico = form.cleaned_data['CursoAcademico']

            try:
                # Process the CSV file
                encoding = get_encoding(archivo_csv)
                archivo_csv.seek(0)  # Rewind the file pointer
                csvfile = TextIOWrapper(archivo_csv, encoding=encoding)
                reader = csv.DictReader(csvfile)

                data = {'nro_registros': 0, 'datos': []}
                for row in reader:
                    datos_alumno = {}
                    for key, value in row.items():
                        try:
                            datos_alumno[key] = value
                        except (ValueError, KeyError):
                            print(f"Error processing row: {row}")  # Log error for debugging
                            continue  # Skip invalid rows

                    datos_alumno['Curso Academico'] = curso_academico.nombre
                    data['datos'].append(datos_alumno)
                    data['nro_registros'] += 1

                return JsonResponse(data)

            except Exception as e:
                print(f"Error procesando CSV: {e}")  # Log the error for debugging
                return JsonResponse({'error': 'Ha ocurrido un error al procesar el archivo.'}, status=500)
    else:
        form = CargaRegAlumSeneca()
    return render(request, 'RegAlum.html', {'form': form, 'menu_carga': True})

@staff_member_required
def RegAlum_procesar_datos(request):
    if request.method == 'POST':
        # Obtener los datos del cuerpo de la solicitud
        data = json.loads(request.body)
        unidad = data['Unidad']
        repetidor = int(data['Nº de matrículas en este curso']) > 1
        edad = int(data['Edad a 31/12 del año de matrícula'])
        sexo = data['Sexo']

        curso_academico = CursoAcademico.objects.filter(nombre=data['Curso Academico']).first()
        if not curso_academico:
            return JsonResponse({'error': f'Curso Academico :{data["Curso Academico"]} no existe.'})

        alumno = Alumnos.objects.filter(Nombre=data['Alumno/a']).first()
        if not alumno:
            return JsonResponse({'error': f'El alumno :{data["Alumno/a"]} no existe.'})

        nivel = Niveles.objects.filter(
            Q(Nombre=data['Curso']) | Q(NombresAntiguos__icontains=data['Curso'])
        ).first()

        info_alumno, creado = InfoAlumnos.objects.get_or_create(
            curso_academico=curso_academico,
            Alumno=alumno,
            defaults={
                'Nivel': nivel,
                'Unidad': unidad,
                'Repetidor': repetidor,
                'Edad': edad,
                'Sexo': sexo
            }
        )
        if not creado:
            info_alumno.Unidad = unidad
            info_alumno.Repetidor = repetidor
            info_alumno.Edad = edad
            info_alumno.Sexo = sexo
            info_alumno.Nivel = nivel
            info_alumno.save()

        return JsonResponse({'status': 'success'})

    else:
        # Manejar otros métodos HTTP (si es necesario)
        return JsonResponse({'error': 'Método no permitido'})

@staff_member_required
def admision(request):
    if request.method == 'POST':
        form = CargaAdmisionSeneca(request.POST, request.FILES)
        if form.is_valid():
            archivo_csv_1_eso = form.cleaned_data['ArchivoCSV_1_ESO']
            archivo_csv_3_eso = form.cleaned_data['ArchivoCSV_3_ESO']
            archivo_csv_1_bto_cyt = form.cleaned_data['ArchivoCSV_1_BTO_CyT']
            archivo_csv_1_bto_hycs = form.cleaned_data['ArchivoCSV_1_BTO_HyCS']
            curso_academico = form.cleaned_data['CursoAcademico']

            try:
                data = {'nro_registros': 0, 'datos': []}
                archivos = [archivo_csv_1_eso, archivo_csv_3_eso, archivo_csv_1_bto_cyt, archivo_csv_1_bto_hycs]
                # Process the CSV files
                for archivo in archivos:
                    encoding = get_encoding(archivo)
                    archivo.seek(0)  # Rewind the file pointer
                    csvfile = TextIOWrapper(archivo, encoding=encoding)
                    reader = csv.DictReader(csvfile)


                    for row in reader:
                        datos_alumno = {}
                        for key, value in row.items():
                            if key in ['Alumno/a', 'Centro de procedencia']:
                                try:
                                    datos_alumno[key] = value
                                except (ValueError, KeyError):
                                    print(f"Error processing row: {row}")  # Log error for debugging
                                    continue  # Skip invalid rows

                        datos_alumno['Curso Academico'] = curso_academico.nombre
                        data['datos'].append(datos_alumno)
                        data['nro_registros'] += 1

                return JsonResponse(data)
            except Exception as e:
                print(f"Error procesando CSV: {e}")  # Log the error for debugging
                return JsonResponse({'error': 'Ha ocurrido un error al procesar el archivo.'}, status=500)
    else:
        form = CargaAdmisionSeneca()
    return render(request, 'admision.html', {'form': form, 'menu_carga': True})
def admision_procesar_datos(request):
    if request.method == 'POST':
        # Obtener los datos del cuerpo de la solicitud
        data = json.loads(request.body)

        curso_academico = CursoAcademico.objects.filter(nombre=data['Curso Academico']).first()
        if not curso_academico:
            return JsonResponse({'error': f'El curso académico :{data["Curso Academico"]} no existe.'})

        alumno = Alumnos.objects.filter(Nombre=data['Alumno/a']).first()
        if not alumno:
            return JsonResponse({'error': f'El alumno :{data["Alumno/a"]} no existe.'})

        lst = data['Centro de procedencia'].split(' - ')
        codigo = lst[0]
        nombre = lst[1]
        centro_origen, _ = Centros.objects.get_or_create(
            Nombre=nombre,
            Codigo=codigo,
        )

        info_alumno = InfoAlumnos.objects.filter(
            Q(Alumno=alumno) & Q(curso_academico=curso_academico)
        ).first()
        if not info_alumno:
            return JsonResponse({'error': f'No se ha encontrado información adicional  de {data["Alumno/a"]}.'})

        if info_alumno.Nivel.Abr in ['1º ESO', '3º ESO', '1º BTO CyT', '1º BTO HyCS']:
            info_alumno.CentroOrigen = centro_origen
        else:
            info_alumno.CentroOrigen = None
        info_alumno.save()
        # Añado la info del centro de origen al alumnado de nueva admisión. Esto es válido para alumnado de admisión
        # que no viene del GN. Para el alumnado de BTO que hizo ESO en el GN no vale este procedimiento.
        # ToDo: Hacer script para cargar Centro_ESO al alumnado de BTO o FP que aparezca en info_alumnos en algún curso
        #  anterior al actual.
        if info_alumno.Nivel.Abr in ['1º ESO', '3º ESO']:
            alumno.Centro_EP = centro_origen
            alumno.save()
        if info_alumno.Nivel.Abr in ['1º BTO CyT', '1º BTO HyCS']:
            alumno.Centro_ESO = centro_origen
            alumno.save()

        return JsonResponse({'status': 'success'})

    else:
        # Manejar otros métodos HTTP (si es necesario)
        return JsonResponse({'error': 'Método no permitido'})