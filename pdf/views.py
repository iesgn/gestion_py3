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
import locale

from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from xhtml2pdf import pisa
from io import BytesIO

from absentismo.models import ProtocoloAbs
from centro.models import Alumnos, Cursos, Profesores, Materia, LibroTexto, MateriaImpartida, MatriculaMateria
from centro.utils import get_current_academic_year
from convivencia.models import Amonestaciones, Sanciones
from centro.views import ContarFaltas, group_check_je, group_check_prof, is_tutor, ContarFaltasHistorico, \
    group_check_prof_and_tutor_or_je_or_orientacion
from datetime import datetime
from django.core.mail import EmailMultiAlternatives


# Create your views here.

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


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_partes(request, curso):
    lista_alumnos = Alumnos.objects.filter(Unidad__id=curso)
    lista_alumnos = sorted(lista_alumnos, key=lambda d: d.Nombre)
    ids = [{"id": elem.id} for elem in lista_alumnos]
    lista = zip(range(1, len(lista_alumnos) + 1), lista_alumnos, ContarFaltas(ids))
    data = {'alumnos': lista, 'curso': Cursos.objects.get(id=curso), 'fecha': datetime.now()}
    return imprimir("pdf_partes.html", data, "partes.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_telefonos(request, curso):
    lista_alumnos = Alumnos.objects.filter(Unidad__id=curso)
    lista_alumnos = sorted(lista_alumnos, key=lambda d: d.Nombre)
    lista = zip(range(1, len(lista_alumnos) + 1), lista_alumnos)
    data = {'alumnos': lista, 'curso': Cursos.objects.get(id=curso), 'fecha': datetime.now()}
    return imprimir("pdf_telefonos.html", data, "telefonos.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_historial(request, alum_id, prof):
    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]
    alum = Alumnos.objects.get(pk=alum_id)
    amon = Amonestaciones.objects.filter(IdAlumno_id=alum_id).order_by('Fecha')
    sanc = Sanciones.objects.filter(IdAlumno_id=alum_id).order_by("Fecha")

    historial = list(amon) + list(sanc)
    historial = sorted(historial, key=lambda x: x.Fecha, reverse=False)

    tipo = []
    for h in historial:
        if str(type(h)).split(".")[2][0] == "A":
            tipo.append("A")
        else:
            tipo.append("S")
    hist = zip(historial, tipo, range(1, len(historial) + 1))
    prof = True if prof == "" else False
    data = {'alum': alum, 'historial': hist, 'horas': horas, 'prof': prof}
    return imprimir("pdf_historial.html", data, "historial.pdf", False)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_show(request, tipo, mes, ano, dia):
    fecha = datetime(int(ano), int(mes), int(dia))
    if tipo == "amonestacion":
        datos = Amonestaciones.objects.filter(Fecha=fecha)
        titulo = "Resumen de amonestaciones"
    if tipo == "sancion":
        datos = Sanciones.objects.filter(Fecha=fecha)
        titulo = "Resumen de sanciones"

    datos = zip(range(1, len(datos) + 1), datos, ContarFaltas(datos.values("IdAlumno")),
                ContarFaltasHistorico(datos.values("IdAlumno")))

    data = {'datos': datos, 'tipo': tipo, 'fecha': fecha, 'titulo': titulo, tipo: True}
    return imprimir("pdf_resumen.html", data, "resumen_" + tipo + ".pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_sanciones_hoy(request):
    hoy = datetime.now()
    dict = {}
    dict["Fecha_fin__gte"] = hoy
    dict["Fecha__lte"] = hoy
    datos = Sanciones.objects.filter(**dict).order_by("Fecha")
    titulo = "Alumnos sancionados"
    datos = zip(range(1, len(datos) + 1), datos, [x for x in datos])
    data = {'datos': datos, 'tipo': "sancion", 'fecha': hoy, 'titulo': titulo}
    return imprimir("pdf_resumen.html", data, "resumen_sancion_hoy.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def carta_amonestacion(request, mes, ano, dia, todos):
    info = {}
    contenido = ""
    fecha2 = datetime(int(ano), int(mes), int(dia))
    info["fecha"] = "%s/%s/%s" % (dia, mes, ano)
    lista_amonestaciones = Amonestaciones.objects.filter(Fecha=fecha2)
    info["amonestaciones"] = []
    for amonestacion in lista_amonestaciones:
        if todos == "n" and amonestacion.IdAlumno.email == "":
            info["amonestaciones"].append(amonestacion)
        if todos == "s":
            info["amonestaciones"].append(amonestacion)

    for a in info["amonestaciones"]:
        info2 = {}
        info2["amonestacion"] = a
        info2["num_amon"] = len(Amonestaciones.objects.filter(IdAlumno_id=a.IdAlumno.id))
        template = get_template("pdf_contenido_carta_amonestacion.html")
        contenido = contenido + template.render(Context(info2).flatten())
        if a.IdAlumno.id != info["amonestaciones"][-1].id:
            contenido = contenido + "<pdf:nextpage>"
    info["contenido"] = contenido
    return imprimir("pdf_carta.html", info, "carta_amonestacion" + ".pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def send_amonestacion(request, mes, ano, dia):
    info = {}
    contenido = ""
    fecha2 = datetime(int(ano), int(mes), int(dia))
    info["fecha"] = "%s/%s/%s" % (dia, mes, ano)
    info["amonestaciones"] = Amonestaciones.objects.filter(Fecha=fecha2)

    info["enviados"] = []
    info["noemail"] = []
    info["yaenviados"] = []
    for i in info["amonestaciones"]:
        info2 = {}
        info2["amonestacion"] = i
        info2["num_amon"] = len(Amonestaciones.objects.filter(IdAlumno_id=i.IdAlumno.id))
        template = get_template("pdf_contenido_carta_amonestacion.html")
        contenido = template.render(Context(info2).flatten())
        asunto = "IES Gonzalo Nazareno. Amonestación: " + i.IdAlumno.Nombre + " - Hora:" + i.Hora

        # Se envía el correo
        if len(i.IdAlumno.email) > 0 and not i.Enviado:
            try:
                msg = ""
                msg = EmailMultiAlternatives(
                    asunto,
                    contenido,
                    '41011038.jestudios.edu@juntadeandalucia.es',
                    [i.IdAlumno.email]
                )

                msg.attach_alternative(contenido, "text/html")
                # msg.send(fail_silently=False)
                # 8/4/2021
                i.Enviado = True
                i.save()
                info["enviados"].append({'Nombre': i.IdAlumno.Nombre, 'email': i.IdAlumno.email})

            except:
                pass
        # Ya se ha enviado
        elif len(i.IdAlumno.email) > 0 and i.Enviado:
            info["yaenviados"].append({'Nombre': i.IdAlumno.Nombre, 'email': i.IdAlumno.email})
        elif len(i.IdAlumno.email) == 0:
            info["noemail"].append({'Nombre': i.IdAlumno.Nombre, 'email': i.IdAlumno.email})
    context = {"info": info, "url": "/convivencia/show/amonestacion/" + str(mes) + "/" + str(ano) + "/" + str(dia)}
    return render(request, "send_amonestacion.html", context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def carta_sancion(request, identificador):
    info2 = {}
    info2["sancion"] = Sanciones.objects.get(id=identificador)
    info = {}
    template = get_template("pdf_contenido_carta_sancion.html")
    info["contenido"] = template.render(Context(info2).flatten())
    return imprimir("pdf_carta.html", info, "carta_sancion.pdf", False)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def infoIA(request, alum_id):
    curso_academico_actual = get_current_academic_year()
    # Obtener el alumno
    alumno = get_object_or_404(Alumnos, id=alum_id)

    # Obtener amonestaciones y sanciones del alumno
    amonestaciones = Amonestaciones.objects.filter(
        IdAlumno=alumno, curso_academico=curso_academico_actual
    ).order_by("Fecha")
    sanciones = Sanciones.objects.filter(
        IdAlumno=alumno, curso_academico=curso_academico_actual
    ).order_by("Fecha")

    # Crear contenido del archivo
    contenido = "AMONESTACIONES\n"
    for amonestacion in amonestaciones:
        fecha_formateada = amonestacion.Fecha.strftime('%d/%m/%Y')
        contenido += f"{fecha_formateada}: {amonestacion.Tipo.TipoAmonestacion} (conducta {amonestacion.gravedad}). {amonestacion.Comentario}\n"

    contenido += "\nSANCIONES\n"
    for sancion in sanciones:
        fecha_formateada = sancion.Fecha.strftime('%d/%m/%Y')
        contenido += f"{fecha_formateada}: {sancion.Sancion}\n"

    # Crear respuesta con el archivo TXT
    response = HttpResponse(contenido, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'inline; filename="info_{alumno.Nombre}.txt"'
    return response


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def imprimir_profesores(request):
    lista_profesores = Profesores.objects.filter(Baja=False).exclude(Apellidos="-").order_by("Apellidos")
    texto = "Listado de profesores"
    if request.path.split("/")[2] == "claustro":
        lista_profesores = lista_profesores.exclude(Baja=True)
        texto = 'Asistencia a claustro'
        data = {'texto': texto, 'profesores': lista_profesores, 'fecha': datetime.now(),
                "resto": len(lista_profesores) % 3}
    elif request.path.split("/")[2] == "semana":
        lista_profesores = lista_profesores.exclude(Baja=True)
        texto = 'Asistencia semanal'
        data = {'texto': texto, 'profesores': lista_profesores, 'fecha': datetime.now(),
                "resto": len(lista_profesores) % 3}
    else:
        data = {'texto': texto, 'profesores': lista_profesores, 'fecha': datetime.now(),
                "resto": len(lista_profesores) % 3}
    return imprimir("pdf_" + request.path.split("/")[2] + ".html", data, request.path.split("/")[2] + ".pdf")


def imprimir(temp, data, title, descarga=True):
    template = get_template(temp)
    pdf_data = template.render(Context(data).flatten())

    # Write PDF to file
    pdf = BytesIO()

    response = HttpResponse(pdf.read(), content_type='application/pdf')
    if descarga:
        response['Content-Disposition'] = 'attachment; filename="' + title + '"'
    else:
        response['Content-Disposition'] = 'inline; filename="' + title + '"'
    try:
        pisa.CreatePDF(pdf_data, dest=response)
    except:
        return HttpResponse('Errors')
    return response


@login_required(login_url='/')
@user_passes_test(group_check_prof_and_tutor_or_je_or_orientacion, login_url='/')
def carta_abs_tutor_familia(request, proto_id):
    # locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    protocolo = ProtocoloAbs.objects.get(id=proto_id)

    info2 = {
        "protocolo": protocolo,
        "destinatarios": protocolo.alumno.Nombre.split(", ")[0]
    }

    # Captura fecha y hora de los parámetros GET
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora")
    if fecha and hora:
        # Convierte la fecha y hora en el formato deseado
        fecha_obj = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        dia = fecha_obj.strftime("%d")
        mes_en_ingles = fecha_obj.strftime("%B")  # Mes en inglés
        mes = meses_es[mes_en_ingles]  # Traducir al español
        hora_formateada = fecha_obj.strftime("%H:%M")

        info2["dia_reunion"] = f"{dia}"
        info2["mes_reunion"] = f"{mes}"
        info2["hora_reunion"] = f"{hora_formateada}"
    else:
        info2["dia_reunion"] = f"____"
        info2["mes_reunion"] = f"____________________"
        info2["hora_reunion"] = f"__________"

    template = get_template("pdf_contenido_carta_abs_tutor_familia.html")
    info = {"contenido": template.render(Context(info2).flatten())}
    return imprimir("pdf_carta.html", info, "carta_abs_tutor_familias.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_prof_and_tutor_or_je_or_orientacion, login_url='/')
def carta_abs_tutor_ED(request, proto_id):
    # locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    protocolo = ProtocoloAbs.objects.get(id=proto_id)

    info2 = {
        "protocolo": protocolo
    }

    # Captura fecha de los parámetros GET
    fecha = request.GET.get("fecha")

    if fecha:
        # Convierte la fecha y hora en el formato deseado
        fecha_obj = datetime.strptime(f"{fecha}", "%Y-%m-%d")
        dia = fecha_obj.strftime("%d")
        mes_en_ingles = fecha_obj.strftime("%B")  # Mes en inglés
        mes = meses_es[mes_en_ingles]  # Traducir al español

        info2["fecha_convocado"] = f"{dia} de {mes}"

    else:
        info2["fecha_convocado"] = f"_________________________"

    template = get_template("pdf_contenido_carta_abs_tutor_ED.html")
    info = {"contenido": template.render(Context(info2).flatten())}
    return imprimir("pdf_carta.html", info, "carta_abs_tutor_ED.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def carta_abs_ED_familia(request, proto_id):
    # locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    profesor = request.user.profesor

    protocolo = ProtocoloAbs.objects.get(id=proto_id)

    info2 = {
        "protocolo": protocolo,
        "destinatarios": protocolo.alumno.Nombre.split(", ")[0]
    }

    # Captura fecha y hora de los parámetros GET
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora")
    if fecha and hora:
        # Convierte la fecha y hora en el formato deseado
        fecha_obj = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        dia = fecha_obj.strftime("%d")
        mes_en_ingles = fecha_obj.strftime("%B")  # Mes en inglés
        mes = meses_es[mes_en_ingles]  # Traducir al español
        hora_formateada = fecha_obj.strftime("%H:%M")

        info2["dia_reunion"] = f"{dia}"
        info2["mes_reunion"] = f"{mes}"
        info2["hora_reunion"] = f"{hora_formateada}"
    else:
        info2["dia_reunion"] = f"____"
        info2["mes_reunion"] = f"____________________"
        info2["hora_reunion"] = f"__________"

    info2["nombre_jefe"] = profesor

    template = get_template("pdf_contenido_carta_abs_ED_familia.html")
    info = {"contenido": template.render(Context(info2).flatten())}
    return imprimir("pdf_carta.html", info, "carta_abs_ED_familias.pdf")


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def hoja_firmas_revision_libros(request):
    profesor_id = request.GET.get('profesor_id')
    curso_id = request.GET.get('curso_id')
    materia_id = request.GET.get('materia_id')
    libro_id = request.GET.get('libro_id')


    curso_academico_actual = get_current_academic_year()

    if not all([profesor_id, curso_id, materia_id, libro_id]):
        return HttpResponse('Faltan datos para generar la hoja de firmas.', status=400)

    profesor = Profesores.objects.get(pk=profesor_id)
    materia = Materia.objects.get(pk=materia_id)
    curso = Cursos.objects.get(pk=curso_id)
    libro = LibroTexto.objects.get(pk=libro_id)


    # Buscar la MateriaImpartida concreta
    try:
        materia_impartida = MateriaImpartida.objects.get(
            profesor=profesor,
            materia=materia,
            curso=curso,
            curso_academico=curso_academico_actual
        )
    except MateriaImpartida.DoesNotExist:
        return HttpResponse('No se encontró la asignación de materia para este profesor y curso.', status=404)

    # Obtener el listado preciso de alumnos
    matriculas = MatriculaMateria.objects.filter(
        materia_impartida=materia_impartida,
        curso_academico=curso_academico_actual
    ).select_related('alumno').order_by('alumno__Nombre')

    alumnos = [m.alumno for m in matriculas]

    context_interno = {
        "profesor": profesor,
        "curso": curso,
        "materia": materia,
        "libro": libro,
        "curso_academico": curso_academico_actual,
        "alumnos": list(enumerate(alumnos, 1))
    }

    template = get_template("pdf_hoja_firmas_revision_libros.html")
    contenido_renderizado = template.render(Context(context_interno).flatten())
    contexto_base = {"contenido": contenido_renderizado}

    return imprimir("pdf_carta.html", contexto_base, "hoja_firmas.pdf", descarga=True)