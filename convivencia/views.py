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
from sqlite3 import IntegrityError

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from centro.utils import get_current_academic_year, get_previous_academic_years
from convivencia.forms import AmonestacionForm, SancionForm, FechasForm, AmonestacionProfeForm, ResumenForm, \
    IntervencionAulaHorizonteForm
from centro.models import Alumnos, Profesores, Niveles, CursoAcademico, MateriaImpartida
from centro.views import group_check_je, group_check_prof, group_check_prof_and_tutor_or_je
from convivencia.models import Amonestaciones, Sanciones, TiposAmonestaciones, PropuestasSancion, \
    IntervencionAulaHorizonte
from centro.models import Cursos
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from datetime import datetime, date, timedelta
from operator import itemgetter
from django.db.models import Count, Q
from django.template.loader import get_template
from django.shortcuts import render
from django.template import Context
from django.core.mail import send_mail
from datetime import date
import time


# Create your views here.

def procesar_amonestacion(amon):
    # Obtener el curso académico del alumno
    curso_academico = get_current_academic_year()

    # Obtener los profesores del curso donde el alumno está matriculado
    curso = amon.IdAlumno.Unidad  # Obtener el curso (Unidad) del alumno
    # Filtramos los profesores que están asignados a ese curso en el curso académico actual
    destinatarios = list(MateriaImpartida.objects.filter(curso=curso, curso_academico=curso_academico)
                         .values_list('profesor', flat=True))

    # Añadir al tutor del alumno
    destinatarios.append(curso.Tutor.id)

    # Obtener las direcciones de correo electrónico de los destinatarios
    correos = []
    for prof_id in destinatarios:
        profe = Profesores.objects.get(id=prof_id)
        correo = profe.Email
        if correo:
            correos.append(correo)

    # Preparar el correo para los destinatarios de la amonestación
    template = get_template("correo_amonestacion.html")
    contenido = template.render({'amon': amon})

    try:
        send_mail(
            'Nueva amonestación',
            contenido,
            '41011038.jestudios.edu@juntadeandalucia.es',
            correos,
            fail_silently=False,
        )
    except ConnectionRefusedError:
        print("Error al enviar el correo")

    # Enviar amonestaciones graves a Jefatura de Estudios (JE)
    if amon.Tipo.TipoAmonestacion in [
        'Acoso escolar',
        'Agresión física a algún miembro de la comunidad educativa',
        'Amenaza o coacción a algún miembro de la comunidad educativa',
        'Injurias y ofensas hacia miembro del IES',
        'Vejaciones o humillaciones a una persona',
        'Actuaciones perjudiciales para la salud y la integridad'
    ]:
        JE = Group.objects.get(name="jefatura de estudios")
        JEs = User.objects.filter(groups=JE).all()
        destinatarios_je = list(JEs)

        # Preparar el correo para la Jefatura de Estudios (JE)
        template = get_template("correo_amonestacion_grave.html")
        contenido = template.render({'amon': amon})

        correos_je = []
        for prof in destinatarios_je:
            profe = Profesores.objects.filter(user=prof).first()
            correo = profe.Email
            if correo and 'g.educaand.es' in correo:
                correos_je.append(correo)

        try:
            send_mail(
                'AMONESTACIÓN GRAVE',
                contenido,
                '41011038.jestudios.edu@juntadeandalucia.es',
                correos_je,
                fail_silently=False,
            )
        except ConnectionRefusedError:
            print("Error al enviar el correo")


# Curro Jul 24: Modifico para que solo pueda usarse por JE
@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def parte(request, tipo, alum_id):
    alum = Alumnos.objects.get(pk=alum_id)

    if request.method == 'POST':
        if tipo == "amonestacion":
            form = AmonestacionForm(request.POST)
            titulo = "Amonestaciones"
        elif tipo == "sancion":
            form = SancionForm(request.POST)
            titulo = "Sanciones"
        else:
            return redirect("/")

        if form.is_valid():
            if tipo == "amonestacion":
                # Comprobar si ya existe una amonestación similar para evitar duplicados
                if not Amonestaciones.objects.filter(IdAlumno=form.cleaned_data['IdAlumno'],
                                                     Fecha=form.cleaned_data['Fecha'],
                                                     Profesor=form.cleaned_data['Profesor'],
                                                     Hora=form.cleaned_data['Hora'],
                                                     Tipo=form.cleaned_data['Tipo'],
                                                     Comentario=form.cleaned_data['Comentario']).exists():
                    try:
                        form.save()

                        amon = form.instance
                        procesar_amonestacion(amon)

                    except IntegrityError:
                        print("Ya existe una amonestación igual")

            if tipo == "sancion":
                try:
                    form.save()
                    sanc = form.instance

                    # Obtener los profesores del curso académico y la unidad del alumno
                    curso_academico = get_current_academic_year()
                    curso = alum.Unidad  # Obtener la unidad del alumno (curso)
                    # Filtramos los profesores que imparten asignaturas en ese curso académico
                    destinatarios = list(MateriaImpartida.objects.filter(curso=curso, curso_academico=curso_academico)
                                         .values_list('profesor', flat=True))
                    destinatarios.append(curso.Tutor.id)

                    # Preparar el correo para los destinatarios de la sanción
                    template = get_template("correo_sancion.html")
                    contenido = template.render({'sanc': sanc})

                    correos = []
                    for prof_id in destinatarios:
                        profe = Profesores.objects.get(id=prof_id)
                        correo = profe.Email
                        if correo:
                            correos.append(correo)

                    try:
                        send_mail(
                            'Nueva sanción',
                            contenido,
                            '41011038.jestudios.edu@juntadeandalucia.es',
                            correos,
                            fail_silently=False,
                        )
                    except ConnectionRefusedError:
                        print("Error de conexión al enviar el correo")

                except IntegrityError:
                    print("Ya existe una sanción igual")

            return redirect('/centro/alumnos')

    else:
        if tipo == "amonestacion":
            profe = Profesores.objects.filter(user=request.user).first()
            form = AmonestacionForm({'IdAlumno': alum.id, 'Fecha': time.strftime("%d/%m/%Y"), 'Hora': 1, 'Profesor': profe.id})
            titulo = "Amonestaciones"
        elif tipo == "sancion":
            form = SancionForm({'IdAlumno': alum.id, 'Fecha': time.strftime("%d/%m/%Y"), 'Fecha_fin': time.strftime("%d/%m/%Y"),
                                'Profesor': 1})
            titulo = "Sanciones"
        else:
            return redirect("/")

    context = {'alum': alum, 'form': form, 'titulo': titulo, 'tipo': tipo, 'menu_convivencia': True}
    return render(request, 'parte.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def historial(request, alum_id, prof):
    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]
    alum = Alumnos.objects.get(pk=alum_id)

    # Comprueba si el usuario pertenece a 'jefatura de estudios'
    es_jefatura = request.user.groups.filter(name="jefatura de estudios").exists()

    # Comprueba si es tutor de la unidad del alumno
    es_tutor = False
    if alum.Unidad and alum.Unidad.Tutor:
        # Dependiendo de cómo se vincule Profesor usuario, ajuste aquí:
        es_tutor = request.user == alum.Unidad.Tutor.user  # si Tutor tiene FK a User
        # Si no, usar: request.user.username == alum.Unidad.Tutor.UsuarioDjango.username (ajustar según tu modelo)


    # Si no es tutor ni jefatura, redirigir a la página previa o a homepage
    if not (es_tutor or es_jefatura):
        # Intentar redirigir a la página anterior, o "/" si no hay referrer
        return redirect(request.META.get('HTTP_REFERER', '/'))


    curso_academico_actual = get_current_academic_year()

    # Filtrar las amonestaciones y sanciones del curso académico actual
    amon_actual = Amonestaciones.objects.filter(IdAlumno_id=alum_id, curso_academico=curso_academico_actual).order_by(
        'Fecha')
    sanc_actual = Sanciones.objects.filter(IdAlumno_id=alum_id, curso_academico=curso_academico_actual).order_by(
        'Fecha')

    historial_actual = list(amon_actual) + list(sanc_actual)
    historial_actual = sorted(historial_actual, key=lambda x: x.Fecha, reverse=False)

    tipo_actual = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_actual]
    hist_actual = zip(historial_actual, tipo_actual, range(1, len(historial_actual) + 1))

    # Filtrar las amonestaciones y sanciones de cursos anteriores
    cursos_anteriores = get_previous_academic_years()
    historial_anteriores = {}

    for curso in cursos_anteriores:
        amon_anteriores = Amonestaciones.objects.filter(IdAlumno_id=alum_id, curso_academico=curso).order_by('Fecha')

        sanc_anteriores = Sanciones.objects.filter(IdAlumno_id=alum_id, curso_academico=curso).order_by('Fecha')

        historial_curso = list(amon_anteriores) + list(sanc_anteriores)
        historial_curso = sorted(historial_curso, key=lambda x: x.Fecha, reverse=False)

        tipo_anteriores = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_curso]
        hist_anteriores = list(zip(historial_curso, tipo_anteriores, range(1, len(historial_curso) + 1)))

        if hist_anteriores:
            historial_anteriores[curso] = hist_anteriores


    prof = True if prof == "" else False

    context = {
        'prof': prof,
        'alum': alum,
        'historial_actual': hist_actual,
        'historial_anteriores': historial_anteriores,
        'menu_convivencia': True,
        'horas': horas
    }

    return render(request, 'historial.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def resumen_hoy(request, tipo):
    hoy = datetime.now()
    return resumen(request, tipo, str(hoy.month), str(hoy.year))


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def resumen(request, tipo=None, fecha=None):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        fecha = request.POST.get('fecha')
        form = ResumenForm(request.POST)
        if form.is_valid():
            # Procesar los datos del formulario aquí si es necesario
            pass
    else:
        # Valores predeterminados para GET
        tipo = tipo if tipo else 'amonestacion'
        hoy = datetime.now()
        # Formatear la fecha
        fecha_formateada = hoy.strftime('%d-%m-%Y')
        # Redirigir a POST con valores predeterminados solo si es GET
        if not fecha:
            return redirect('resumen_con_parametros', tipo=tipo, fecha=fecha_formateada)

        form = ResumenForm(initial={'tipo': tipo, 'fecha': hoy})

    context = {'form': form, 'tipo': tipo, 'fecha': fecha}
    return render(request, 'resumen.html', context)

    '''

    c = calendar.HTMLCalendar(calendar.MONDAY)
    calhtml=c.formatmonth(int(ano),int(mes))

    if tipo=="amonestacion":
        datos=Amonestaciones.objects.filter(Fecha__year=ano).filter(Fecha__month=mes)
        titulo="Resumen de amonestaciones"
    if tipo=="sancion":
        datos=Sanciones.objects.filter(Fecha__year=ano).filter(Fecha__month=mes)
        titulo="Resumen de sanciones"
    
    ult_dia=calendar.monthrange(int(ano),int(mes))[1]
    dic_fechas=datos.values("Fecha")
    fechas=[]
    for f in dic_fechas:
        fechas.append(f["Fecha"])

    for dia in range(1,int(ult_dia)+1):
        fecha=datetime(int(ano),int(mes),dia)
        if fecha.date() in fechas:
            calhtml=calhtml.replace(">"+str(dia)+"<",'><a href="/convivencia/show/%s/%s/%s/%s"><strong>%s</strong></a><'%(tipo,mes,ano,dia,dia))
    calhtml=calhtml.replace('class="month"','class="table-condensed table-bordered table-striped"')
    
    
    mes_actual=datetime(int(ano),int(mes),1)
    mes_ant=AddMonths(mes_actual,-1)
    mes_prox=AddMonths(mes_actual,1)

    context={'calhtml':calhtml,'fechas':[mes_actual,mes_ant,mes_prox],'titulo':titulo,'tipo':tipo,'menu_resumen':True}
    return render(request, 'resumen.html',context)
    '''


def AddMonths(d, x):
    newmonth = (((d.month - 1) + x) % 12) + 1
    newyear = int(d.year + (((d.month - 1) + x) / 12))
    return datetime(newyear, newmonth, d.day)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def show(request, tipo=None, mes=None, ano=None, dia=None):
    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]

    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        tipo = request.POST.get('tipo')
        dia, mes, ano = fecha.split('/')
        return redirect('show', tipo=tipo, mes=mes, ano=ano, dia=dia)

    if tipo is None or mes is None or ano is None or dia is None:
        # Establecer valores predeterminados
        tipo = tipo if tipo else 'amonestacion'
        hoy = datetime.now()
        mes = mes if mes else hoy.month
        ano = ano if ano else hoy.year
        dia = dia if dia else hoy.day
        return redirect('show', tipo=tipo, mes=mes, ano=ano, dia=dia)

    fecha = datetime(int(ano), int(mes), int(dia))

    if tipo == "amonestacion":
        datos = Amonestaciones.objects.filter(Fecha=fecha)
        titulo = "Resumen de amonestaciones"
    if tipo == "sancion":

        datos = Sanciones.objects.filter(Fecha=fecha)
        titulo = "Resumen de sanciones"

    form = ResumenForm(initial={'fecha': fecha, 'tipo': tipo})


    # ANTES DEL ZIP:
    curso_academico_actual = get_current_academic_year()

    contar_actual = []
    contar_hist = []
    numeros = []

    for i, d in enumerate(datos, 1):
        id_alum = d.IdAlumno_id  # Directo del objeto, MISMO ORDEN

        if id_alum:
            # Actual
            am = Amonestaciones.objects.filter(IdAlumno_id=id_alum,
                                               curso_academico=curso_academico_actual).count()
            sa = Sanciones.objects.filter(IdAlumno_id=id_alum,
                                          curso_academico=curso_academico_actual).count()
            contar_actual.append(f"{am}/{sa}")

            # Histórico
            am_hist = Amonestaciones.objects.filter(IdAlumno_id=id_alum).count()
            sa_hist = Sanciones.objects.filter(IdAlumno_id=id_alum).count()
            contar_hist.append(f"{am_hist}/{sa_hist}")
        else:
            contar_actual.append("0/0")
            contar_hist.append("0/0")

        numeros.append(i)

    datos = zip(numeros, datos, contar_actual, contar_hist)

    #datos = zip(range(1, len(datos) + 1), datos, ContarFaltas(datos.values("IdAlumno")), ContarFaltasHistorico(datos.values("IdAlumno")))
    context = {
        'form': form,
        'datos': datos,
        'tipo': tipo,
        'mes': mes,
        'ano': ano,
        'dia': dia,
        'titulo': titulo,
        'horas' : horas,
        f'menu_{tipo}': True,
        'menu_convivencia': True,

    }
    context[tipo] = True





    return render(request, 'show.html', context)


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

        # f1=datetime(int(request.POST.get('Fecha1_year')),int(request.POST.get('Fecha1_month')),int(request.POST.get('Fecha1_day')))
        # f2=datetime(int(request.POST.get('Fecha2_year')),int(request.POST.get('Fecha2_month')),int(request.POST.get('Fecha2_day')))
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')

        a3t = Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count()
        al3t = Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="L").count()
        ag3t = Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="G").count()
        s3t = Sanciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count()
        sne3t = Sanciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado,
                                         NoExpulsion=True).count()

        datos1t = a3t, al3t, ag3t, s3t, sne3t
        datos2t = a3t, al3t, ag3t, s3t, sne3t
        datos3t = a3t, al3t, ag3t, s3t, sne3t

        form = FechasForm(request.POST, curso_academico=curso_seleccionado)
        fechas = [f1, f2]
        total = ()

        tipos = []
        for i in TiposAmonestaciones.objects.all():
            tipos.append((i.TipoAmonestacion,
                          Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2,
                                                        curso_academico=curso_seleccionado,
                                                        Tipo=i).count(),
                          i.TipoFalta
                          ))
        filtro = True
    else:
        # Valores por defecto
        year1 = curso_seleccionado.año_inicio
        fi1 = datetime(year1, 9, 1)
        ff1 = datetime(year1, 12, 31)
        fi2 = datetime(year1 + 1, 1, 1)
        ff2 = datetime(year1 + 1, 3, 31)
        fi3 = datetime(year1 + 1, 4, 1)
        ff3 = datetime(year1 + 1, 6, 30)

        # Numeros 1er trimestre

        a1t = Amonestaciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1,
                                            curso_academico=curso_seleccionado).count()
        al1t = Amonestaciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="L").count()
        ag1t = Amonestaciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="G").count()
        s1t = Sanciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1, curso_academico=curso_seleccionado).count()
        sne1t = Sanciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1, curso_academico=curso_seleccionado,
                                         NoExpulsion=True).count()

        datos1t = a1t, al1t, ag1t, s1t, sne1t

        # Numeros 2do trimestre

        a2t = Amonestaciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2,
                                            curso_academico=curso_seleccionado).count()
        al2t = Amonestaciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="L").count()
        ag2t = Amonestaciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="G").count()
        s2t = Sanciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2, curso_academico=curso_seleccionado).count()
        sne2t = Sanciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2, curso_academico=curso_seleccionado,
                                         NoExpulsion=True).count()

        datos2t = a2t, al2t, ag2t, s2t, sne2t

        # Numeros 3er trimestre

        a3t = Amonestaciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3,
                                            curso_academico=curso_seleccionado).count()
        al3t = Amonestaciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="L").count()
        ag3t = Amonestaciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3, curso_academico=curso_seleccionado,
                                             Tipo__TipoFalta="G").count()
        s3t = Sanciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3, curso_academico=curso_seleccionado).count()
        sne3t = Sanciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3, curso_academico=curso_seleccionado,
                                         NoExpulsion=True).count()

        datos3t = a3t, al3t, ag3t, s3t, sne3t

        form = FechasForm(curso_academico=curso_seleccionado)
        fechas = [fi1, ff3]
        total = Amonestaciones.objects.filter(curso_academico=curso_seleccionado).count(), Sanciones.objects.filter(
            curso_academico=curso_seleccionado).count(), Sanciones.objects.filter(
            curso_academico=curso_seleccionado, NoExpulsion=True).count()
        filtro = False

        # Tipos de amonestaciones
        tipos = []
        for i in TiposAmonestaciones.objects.all():
            tipos.append((
                i.TipoAmonestacion,
                Amonestaciones.objects.filter(Fecha__gte=fi1, Fecha__lte=ff1, curso_academico=curso_seleccionado,
                                              Tipo=i).count(),
                Amonestaciones.objects.filter(Fecha__gte=fi2, Fecha__lte=ff2, curso_academico=curso_seleccionado,
                                              Tipo=i).count(),
                Amonestaciones.objects.filter(Fecha__gte=fi3, Fecha__lte=ff3, curso_academico=curso_seleccionado,
                                              Tipo=i).count(),
                i.TipoFalta
            ))

    context = {'filtro': filtro, 'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos, 'tipos': tipos, 'total': total, 'form': form, 'datos1t': datos1t,
               'datos2t': datos2t,
               'datos3t': datos3t, 'fechas': fechas, 'menu_estadistica': True}

    return render(request, 'estadisticas.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def estadisticas2(request, curso):
    if request.method == "POST":

        pass
    else:
        year1 = int(curso) - 1
        fi1 = datetime(year1, 9, 1)
        ff1 = datetime(year1, 12, 31)
        fi2 = datetime(year1 + 1, 1, 1)
        ff2 = datetime(year1 + 1, 3, 31)
        fi3 = datetime(year1 + 1, 4, 1)
        ff3 = datetime(year1 + 1, 6, 30)

        a1t = Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi1).filter(Fecha__lte=ff1).count()
        a2t = Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi2).filter(Fecha__lte=ff2).count()
        a3t = Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi3).filter(Fecha__lte=ff3).count()
        s1t = Sanciones.objects.using('db%s' % curso).filter(Fecha__gte=fi1).filter(Fecha__lte=ff1).count()
        s2t = Sanciones.objects.using('db%s' % curso).filter(Fecha__gte=fi2).filter(Fecha__lte=ff2).count()
        s3t = Sanciones.objects.using('db%s' % curso).filter(Fecha__gte=fi3).filter(Fecha__lte=ff3).count()
        datos = a1t, s1t, a2t, s2t, a3t, s3t
        form = FechasForm()
        fechas = [fi1, ff3]
        total = Amonestaciones.objects.using('db%s' % curso).count(), Sanciones.objects.using('db%s' % curso).count()
        filtro = False

        # Tipos de amonestaciones
        tipos = []
        for i in TiposAmonestaciones.objects.using('db%s' % curso).all():
            tipos.append((i.TipoAmonestacion,
                          Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi1).filter(
                              Fecha__lte=ff1).filter(Tipo=i).count(),
                          Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi2).filter(
                              Fecha__lte=ff2).filter(Tipo=i).count(),
                          Amonestaciones.objects.using('db%s' % curso).filter(Fecha__gte=fi3).filter(
                              Fecha__lte=ff3).filter(Tipo=i).count(),
                          ))

    context = {'curso': str(int(curso) - 1) + "/" + curso, 'filtro': filtro, 'tipos': tipos, 'total': total,
               'form': form, 'datos': datos, 'fechas': fechas, 'menu_estadistica': True}
    return render(request, 'estadisticas2.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def horas(request):
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
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')

    lista = []
    horas = ["[1ª] Primera", "[2ª] Segunda", "[3ª] Tercera", "Recreo", "[4ª] Cuarta", "[5ª] Quinta", "[6ª] Sexta"]
    for i in range(1, 8):
        if request.method == "POST":
            lista.append(Amonestaciones.objects.filter(Hora=i, Fecha__gte=f1, Fecha__lte=f2,
                                                       curso_academico=curso_seleccionado).count())
        else:
            lista.append(Amonestaciones.objects.filter(Hora=i, curso_academico=curso_seleccionado).count())
    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)
    horas.append("TOTAL")
    if request.method == "POST":
        lista.append(
            Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
    else:
        lista.append(Amonestaciones.objects.filter(curso_academico=curso_seleccionado).count())

    context = {'form': form, 'horas': zip(horas, lista), 'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos, 'totales': lista, 'menu_estadistica': True}
    return render(request, 'horas.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def profesores(request):
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
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')
    lista = []
    if request.method == "POST":
        listAmon = Amonestaciones.objects.values('Profesor').filter(Fecha__gte=f1, Fecha__lte=f2,
                                                                    curso_academico=curso_seleccionado).annotate(
            Count('Profesor'))
    else:
        listAmon = Amonestaciones.objects.values('Profesor').filter(curso_academico=curso_seleccionado).annotate(
            Count('Profesor'))
    newlist = sorted(listAmon, key=itemgetter('Profesor__count'), reverse=True)
    suma = 0
    for l in newlist:
        profesor = Profesores.objects.get(id=l["Profesor"])
        l["Profesor"] = profesor.Apellidos + ", " + profesor.Nombre
        l["Profesor_id"] = profesor.id  # Aquí añades el ID del profesor al diccionario
        suma += l["Profesor__count"]
    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)
    context = {"form": form, "lista": newlist, 'menu_estadistica': True, "suma": suma,
               'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos}
    return render(request, 'lprofesores.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def grupos(request):
    cursos_queryset = Cursos.objects.all()
    cursos_nombres = []

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
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')

    # Total
    total = []
    if request.method == "POST":
        total.append(
            Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
    else:
        total.append(Amonestaciones.objects.filter(curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(curso_academico=curso_seleccionado).count())

    lista = []

    for curso in cursos_queryset:

        if request.method == "POST":
            datos = [Amonestaciones.objects.filter(IdAlumno__in=Alumnos.objects.filter(Unidad=curso)).filter(
                Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count(),
                     Sanciones.objects.filter(IdAlumno__in=Alumnos.objects.filter(Unidad=curso)).filter(
                         Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count()]
        else:
            datos = [Amonestaciones.objects.filter(IdAlumno__in=Alumnos.objects.filter(Unidad=curso),
                                                   curso_academico=curso_seleccionado).count(),
                     Sanciones.objects.filter(IdAlumno__in=Alumnos.objects.filter(Unidad=curso),
                                              curso_academico=curso_seleccionado).count()]
        if total[0] > 0:
            datos.append(round(datos[0] * 100 / total[0], 2))
        else:
            datos.append(0)  # Si total[0] es 0, asigna 0 para evitar división por cero

        if total[1] > 0:
            datos.append(round(datos[1] * 100 / total[1], 2))
        else:
            datos.append(0)  # Si total[1] es 0, asigna 0 para evitar división por cero
        lista.append(datos)

        cursos_nombres.append({
            'nombre': curso.Curso,
            'amonestaciones': datos[0],
            'sanciones': datos[1]
        })

    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)

    cursos = zip(cursos_queryset, lista)
    cursos = sorted(cursos, key=lambda x: x[1][0], reverse=True)
    context = {'form': form, 'cursos': cursos, 'menu_estadistica': True, 'total': total,
               'cursos_nombres': cursos_nombres, 'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos}
    return render(request, 'grupos.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def niveles(request):
    niveles_queryset = Niveles.objects.order_by('Nombre')
    niveles_nombres = []

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
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')

    # Total
    total = []
    if request.method == "POST":
        total.append(
            Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
    else:
        total.append(Amonestaciones.objects.filter(curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(curso_academico=curso_seleccionado).count())

    lista = []

    for nivel in niveles_queryset:

        if request.method == "POST":
            datos = [Amonestaciones.objects.filter(IdAlumno__Unidad__Nivel=nivel).filter(Fecha__gte=f1,
                                                                                         Fecha__lte=f2,
                                                                                         curso_academico=curso_seleccionado).count(),
                     Sanciones.objects.filter(IdAlumno__Unidad__Nivel=nivel).filter(Fecha__gte=f1).filter(
                         Fecha__lte=f2).filter(Fecha__gte=f1, Fecha__lte=f2,
                                               curso_academico=curso_seleccionado).count()]
        else:
            datos = [Amonestaciones.objects.filter(IdAlumno__Unidad__Nivel=nivel,
                                                   curso_academico=curso_seleccionado).count(),
                     Sanciones.objects.filter(IdAlumno__Unidad__Nivel=nivel,
                                              curso_academico=curso_seleccionado).count()]

        if total[0] > 0:
            datos.append(round(datos[0] * 100 / total[0], 2))
        else:
            datos.append(0)  # Si total[0] es 0, asigna 0 para evitar división por cero

        if total[1] > 0:
            datos.append(round(datos[1] * 100 / total[1], 2))
        else:
            datos.append(0)  # Si total[1] es 0, asigna 0 para evitar división por cero

        lista.append(datos)

        niveles_nombres.append({
            'nombre': nivel.Abr,
            'amonestaciones': datos[0],
            'sanciones': datos[1]
        })

    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)

    niveles = zip(niveles_queryset, lista)
    niveles = sorted(niveles, key=lambda x: x[1][0], reverse=True)
    context = {'form': form, 'niveles': niveles, 'menu_estadistica': True, 'total': total,
               'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos, 'niveles_nombres': niveles_nombres}
    return render(request, 'niveles.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def alumnos(request):
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
        f1 = datetime.strptime(request.POST.get('Fecha1'), '%d/%m/%Y')
        f2 = datetime.strptime(request.POST.get('Fecha2'), '%d/%m/%Y')

    # Total
    total = []
    if request.method == "POST":
        total.append(
            Amonestaciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(Fecha__gte=f1, Fecha__lte=f2, curso_academico=curso_seleccionado).count())
    else:
        total.append(Amonestaciones.objects.filter(curso_academico=curso_seleccionado).count())
        total.append(Sanciones.objects.filter(curso_academico=curso_seleccionado).count())

    if request.method == "POST":
        listAmon = Amonestaciones.objects.values('IdAlumno').filter(Fecha__gte=f1, Fecha__lte=f2,
                                                                    curso_academico=curso_seleccionado).annotate(
            Count('IdAlumno'))
        listSan = Sanciones.objects.values('IdAlumno').filter(Fecha__gte=f1, Fecha__lte=f2,
                                                              curso_academico=curso_seleccionado).annotate(
            Count('IdAlumno'))
    else:
        listAmon = Amonestaciones.objects.values('IdAlumno').filter(curso_academico=curso_seleccionado).annotate(
            Count('IdAlumno'))
        listSan = Sanciones.objects.values('IdAlumno').filter(curso_academico=curso_seleccionado).annotate(
            Count('IdAlumno'))
    newlist = sorted(listAmon, key=itemgetter('IdAlumno__count'), reverse=True)
    for l in newlist:
        try:
            l["Sanciones"] = listSan.get(IdAlumno=l["IdAlumno"]).get("IdAlumno__count")
        except:
            l["Sanciones"] = 0
        l["Porcentajes"] = []
        try:
            l["Porcentajes"].append(round(l["IdAlumno__count"] * 100 / total[0], 2))
        except:
            l["Porcentajes"].append(0)
        try:
            l["Porcentajes"].append(round(l["Sanciones"] * 100 / total[1], 2))
        except:
            l["Porcentajes"].append(0)

        try:
            alumno = Alumnos.objects.get(id=l["IdAlumno"])
            unidad = alumno.Unidad
            if unidad:
                l["IdAlumno"] = alumno.Nombre + " (" + unidad.Curso + ")"
                l["IdAlumno_id"] = alumno.id

            else:
                l["IdAlumno"] = alumno.Nombre + " (Sin Unidad asignada)"
                l["IdAlumno_id"] = alumno.id
        except Alumnos.DoesNotExist:
            l["IdAlumno"] = "Alumno no encontrado"
            l["IdAlumno_id"] = 0

    form = FechasForm(request.POST, curso_academico=curso_seleccionado) if request.method == "POST" else FechasForm(
        curso_academico=curso_seleccionado)
    context = {"form": form, "lista": newlist, 'menu_estadistica': True, "suma": total,
               'curso_seleccionado': curso_seleccionado,
               'cursos_academicos': cursos_academicos}
    return render(request, 'lalumnos.html', context)

'''
def ContarFaltas(lista_id):
    curso_academico_actual = get_current_academic_year()

    contar = []
    for alum in lista_id:
        am = str(len(Amonestaciones.objects.filter(IdAlumno_id=list(alum.values())[0], curso_academico=curso_academico_actual)))
        sa = str(len(Sanciones.objects.filter(IdAlumno_id=list(alum.values())[0], curso_academico=curso_academico_actual)))

        contar.append(am + "/" + sa)

    return contar



def ContarFaltasHistorico(lista_id):

    contar = []
    for alum in lista_id:
        am = str(len(Amonestaciones.objects.filter(IdAlumno_id=list(alum.values())[0])))
        sa = str(len(Sanciones.objects.filter(IdAlumno_id=list(alum.values())[0])))

        contar.append(am + "/" + sa)
    return contar
'''

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


# Curro Jul 24: Anado view para que un profesor pueda poner un parte
@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def parteprofe(request, tipo, alum_id):
    alum = Alumnos.objects.get(pk=alum_id)
    profesor = request.user.profesor

    if request.method == 'POST':
        if tipo == "amonestacion":
            form = AmonestacionProfeForm(request.POST)
            titulo = "Amonestaciones"
        else:
            return redirect("/")

        if form.is_valid():
                if tipo == "amonestacion":

                    # Comprobar si ya existe una amonestación similar para evitar duplicados
                    if not Amonestaciones.objects.filter(IdAlumno=form.cleaned_data['IdAlumno'],
                                                         Fecha=form.cleaned_data['Fecha'],
                                                         Profesor=form.cleaned_data['Profesor'],
                                                         Hora=form.cleaned_data['Hora'],
                                                         Tipo=form.cleaned_data['Tipo'],
                                                         Comentario=form.cleaned_data['Comentario']).exists():
                        try:
                            form.save()


                            amon = form.instance
                            procesar_amonestacion(amon)
                        except IntegrityError:
                            print("Ya existe una amonestación igual")

                # Un profe sin perfil JE no puede procesar sanción
                # if tipo == "sancion":
                #     try:
                #         form.save()
                #
                #         sanc = form.instance
                #         destinatarios = list(sanc.IdAlumno.Unidad.EquipoEducativo.filter(Baja=False).all())
                #         destinatarios.append(sanc.IdAlumno.Unidad.Tutor)
                #         template = get_template("correo_sancion.html")
                #         contenido = template.render({'sanc': sanc})
                #
                #         correos = []
                #         for prof in destinatarios:
                #             correo = Profesores.objects.get(id=prof.id).Email
                #             if correo != "":
                #                 correos.append(correo)
                #         send_mail(
                #             'Nueva sanción',
                #             contenido,
                #             '41011038.jestudios.edu@juntadeandalucia.es',
                #             correos,
                #             fail_silently=False,
                #         )
                #     except IntegrityError:
                #         print("Ya existe una sanción igual")
                return redirect('/centro/misalumnos')
    else:
        if tipo == "amonestacion":
            form = AmonestacionProfeForm(
                {'IdAlumno': alum.id, 'Fecha': time.strftime("%d/%m/%Y"), 'Hora': 1, 'Profesor': profesor.id,
                 'ComunicadoFamilia': False})

            titulo = "Amonestaciones"
        else:
            return redirect("/")
        error = False
    context = {'alum': alum, 'form': form, 'titulo': titulo, 'tipo': tipo, 'menu_convivencia': True,
               'profesor': profesor}
    return render(request, 'parteprofe.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def aulaconvivencia(request):
    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]

    curso_academico_actual = get_current_academic_year()

    amonestaciones = Amonestaciones.objects.filter(curso_academico=curso_academico_actual, DerivadoConvivencia=True).order_by('-Fecha')

    context = {
        'amonestaciones': amonestaciones,
        'num_resultados': amonestaciones.count(),
        'menu_convivencia': True,
        'horas': horas,
    }

    return render(request, 'aulaconvivencia.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def misamonestaciones(request):

    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})


    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]

    profesor = request.user.profesor

    curso_academico_actual = get_current_academic_year()

    # Filtrar las amonestaciones y sanciones del curso académico actual
    amon_actual = Amonestaciones.objects.filter(Profesor=profesor, curso_academico=curso_academico_actual).order_by(
        'Fecha')


    historial_actual = list(amon_actual)
    historial_actual = sorted(historial_actual, key=lambda x: x.Fecha, reverse=False)

    tipo_actual = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_actual]
    hist_actual = zip(historial_actual, tipo_actual, range(1, len(historial_actual) + 1))


    prof = True

    context = {
        'profesor' : profesor,
        'prof': prof,
        'historial_actual': hist_actual,
        'menu_convivencia': True,
        'horas': horas
    }

    return render(request, 'misamonestaciones.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def amonestacionesprofe(request, profe_id):


    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]

    profesor = Profesores.objects.get(pk=profe_id)

    curso_academico_actual = get_current_academic_year()

    # Filtrar las amonestaciones y sanciones del curso académico actual
    amon_actual = Amonestaciones.objects.filter(Profesor=profesor, curso_academico=curso_academico_actual).order_by(
        'Fecha')


    historial_actual = list(amon_actual)
    historial_actual = sorted(historial_actual, key=lambda x: x.Fecha, reverse=False)

    tipo_actual = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_actual]
    hist_actual = zip(historial_actual, tipo_actual, range(1, len(historial_actual) + 1))


    prof = True

    context = {
        'profesor' : profesor,
        'prof': prof,
        'historial_actual': hist_actual,
        'menu_convivencia': True,
        'horas': horas
    }

    return render(request, 'amonestacionesprofe.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def sancionesactivas(request):
    hoy = timezone.now().date()  # Obtener la fecha de hoy

    # Filtrar las sanciones activas
    sanciones_activas = Sanciones.objects.filter(Fecha__lte=hoy, Fecha_fin__gte=hoy)

    datos = zip(range(1, len(sanciones_activas) + 1), sanciones_activas)

    context = {
        'sanciones_activas': datos,
        'menu_sanciones': True,  # Si necesitas alguna opción de menú activa
        'menu_convivencia': True,
    }

    return render(request, 'sancionesactivas.html', context)


def calcular_alumnado_sancionable(curso_academico):
    fecha_tope_leves = date.today() - timedelta(days=30)
    fecha_tope_graves = date.today() - timedelta(days=60)

    amonestaciones_sin_caducar = list(
        Amonestaciones.objects.filter(
            Q(curso_academico=curso_academico) & (
                    (Q(Tipo__TipoFalta='L') & Q(Fecha__gt=fecha_tope_leves)) |
                    (Q(Tipo__TipoFalta='G') & Q(Fecha__gt=fecha_tope_graves))
            )).order_by('Fecha').all()
    )

    alumnado = set(am.IdAlumno for am in amonestaciones_sin_caducar)

    fecha_ultima_sancion = {}
    leves = {}
    graves = {}
    fecha_entrada = {}
    amon_movil = {}
    fecha_movil = {}

    for alumno in alumnado:
        fecha_ultima_sancion[alumno] = alumno.ultima_sancion.Fecha if alumno.ultima_sancion is not None else None
        leves[alumno] = 0
        graves[alumno] = 0
        amon_movil[alumno] = 0

    amonestaciones_vivas = defaultdict(list)

    for amonestacion in amonestaciones_sin_caducar:
        alumno = amonestacion.IdAlumno
        if (fecha_ultima_sancion[alumno] is None) or (amonestacion.Fecha > fecha_ultima_sancion[alumno]):
            amonestaciones_vivas[alumno].append(amonestacion)
            if "móvil" in amonestacion.Tipo.TipoAmonestacion:
                amon_movil[alumno] += 1
            if amonestacion.gravedad == 'Leve':
                leves[alumno] += 1
            elif amonestacion.gravedad == 'Grave':
                graves[alumno] += 1

            if (leves[alumno] >= 3 or graves[alumno] >= 1 or amon_movil[alumno] >= 2) and not alumno in fecha_entrada:
            # if ((leves[alumno] + 2 * graves[alumno] >= 4) or amon_movil[alumno] >= 2) and not alumno in fecha_entrada:
                fecha_entrada[alumno] = amonestacion.Fecha

    resultado = {}
    for alumno in amonestaciones_vivas:
        # if (leves[alumno] + 2 * graves[alumno] >= 4) or amon_movil[alumno] >= 2:
        if leves[alumno] >= 3 or graves[alumno] >= 1 or amon_movil[alumno] >= 2:
            resultado[alumno] = {
                'entrada': fecha_entrada[alumno],
                'leves': leves[alumno],
                'graves': graves[alumno],
                'peso': leves[alumno] + 2 * graves[alumno],
                'móvil': amon_movil[alumno] >= 2
            }

    return resultado

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def alumnadosancionable(request, ver_ignorados):
    ver_todas = (ver_ignorados == 'True')
    curso_academico_actual = get_current_academic_year()
    resultado = []
    # Calculo para ver nuevas propuestas
    datos = calcular_alumnado_sancionable(curso_academico_actual)

    if not PropuestasSancion.objects.filter(curso_academico=curso_academico_actual).exists():
        # Cargamos la DB de propuestas por primera vez (no tiene en cuenta el histórico prescrito)
        for alumno in datos:
            propuesta = PropuestasSancion(
                curso_academico=curso_academico_actual,
                alumno=alumno,
                leves=datos[alumno]['leves'],
                graves=datos[alumno]['graves'],
                peso=datos[alumno]['peso'],
                entrada=datos[alumno]['entrada']
            )
            propuesta.save()
            ultima_amonestacion = Amonestaciones.objects.filter(
                IdAlumno=alumno,
                curso_academico=curso_academico_actual
            ).order_by('-Fecha').first()
            resultado.append(
                (
                    alumno,
                    datos[alumno]['leves'],
                    datos[alumno]['graves'],
                    datos[alumno]['peso'],
                    ultima_amonestacion.Fecha,
                    propuesta.id,
                    propuesta.ignorar,
                    datos[alumno].get('móvil', False)
                )
            )
    else:
        # Cargamos todas las propuestas abiertas (sin salida)
        propuestas = PropuestasSancion.objects.filter(
            curso_academico=curso_academico_actual,
            salida=None
        ).all()
        alumnos = [propuesta.alumno for propuesta in propuestas]
        nuevos_alumnos = [alumno for alumno in datos if not alumno in alumnos]

        for alumno in nuevos_alumnos:
            propuesta = PropuestasSancion(
                curso_academico=curso_academico_actual,
                alumno=alumno,
                leves=datos[alumno]['leves'],
                graves=datos[alumno]['graves'],
                peso=datos[alumno]['peso'],
                entrada=datos[alumno]['entrada']
            )
            propuesta.save()
            ultima_amonestacion = Amonestaciones.objects.filter(
                IdAlumno=alumno,
                curso_academico=curso_academico_actual
            ).order_by('-Fecha').first()
            resultado.append(
                (
                    alumno,
                    datos[alumno]['leves'],
                    datos[alumno]['graves'],
                    datos[alumno]['peso'],
                    ultima_amonestacion.Fecha,
                    propuesta.id,
                    propuesta.ignorar,
                    datos[alumno].get('móvil', False)
                )
            )


        for propuesta in propuestas:
            alumno = propuesta.alumno
            if alumno not in datos:
                # El alumno ya no tiene que estar propuesto
                propuesta.salida = date.today()
                propuesta.motivo_salida = "Amonestaciones prescritas."
                propuesta.save()
                continue  # Pasamos al siguiente alumno

            # El alumno estaba propuesto
            if propuesta.ignorar and datos[alumno]['peso'] <= propuesta.peso:
                # Si la propuesta está ignorada y no hay nuevas amonestaciones, solo actualizamos los datos
                propuesta.leves = datos[alumno]['leves']
                propuesta.graves = datos[alumno]['graves']
                propuesta.peso = datos[alumno]['peso']
                propuesta.save()
            else:
                # Si la propuesta no está ignorada o hay nuevas amonestaciones, actualizamos y desactivamos el ignorar
                propuesta.ignorar = False
                propuesta.leves = datos[alumno]['leves']
                propuesta.graves = datos[alumno]['graves']
                propuesta.peso = datos[alumno]['peso']
                propuesta.save()

            # Añadimos el resultado en ambos casos (si la propuesta no está ignorada)
            if ver_todas or not propuesta.ignorar:
                ultima_amonestacion = Amonestaciones.objects.filter(
                    IdAlumno=alumno,
                    curso_academico=curso_academico_actual
                ).order_by('-Fecha').first()
                resultado.append(
                    (
                        alumno,
                        datos[alumno]['leves'],
                        datos[alumno]['graves'],
                        datos[alumno]['peso'],
                        ultima_amonestacion.Fecha,
                        propuesta.id,
                        propuesta.ignorar,
                        datos[alumno].get('móvil', False)
                    )
                )


    resultado.sort(key=lambda x: (int(x[7]), x[3], x[2], x[1]), reverse=True)

    context = {
        'alumnado': resultado,
        'num_resultados': len(resultado),
        'menu_convivencia': True,
        'ver_ignoradas': ver_ignorados == 'True'
    }

    return render(request, 'alumnadosancionable.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def sanciones_reincorporacion(request):
    # Obtener la fecha seleccionada o usar la fecha de hoy si no se proporciona ninguna
    fecha_seleccionada = request.GET.get('fecha')
    if fecha_seleccionada:
        fecha_reincorporacion = timezone.datetime.strptime(fecha_seleccionada, "%Y-%m-%d").date()
    else:
        fecha_reincorporacion = timezone.now().date()

    # Filtrar las sanciones cuya fecha de finalización es el día anterior a la fecha de reincorporación
    sanciones_reincorporacion = Sanciones.objects.filter(Fecha_fin=fecha_reincorporacion - timedelta(days=1))

    # Enumerar las sanciones para mostrarlas en el template
    datos = zip(range(1, len(sanciones_reincorporacion) + 1), sanciones_reincorporacion)

    context = {
        'fecha_reincorporacion': fecha_reincorporacion,
        'sanciones_reincorporacion': datos,
        'menu_convivencia': True,
    }

    return render(request, 'sancionesreincorporacion.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def historial_vigente(request, alum_id, prof):


    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]
    alum = Alumnos.objects.get(pk=alum_id)


    # Comprueba si el usuario pertenece a 'jefatura de estudios'
    es_jefatura = request.user.groups.filter(name="jefatura de estudios").exists()

    # Comprueba si es tutor de la unidad del alumno
    es_tutor = False
    if alum.Unidad and alum.Unidad.Tutor:
        # Dependiendo de cómo se vincule Profesor usuario, ajuste aquí:
        es_tutor = request.user == alum.Unidad.Tutor.user  # si Tutor tiene FK a User
        # Si no, usar: request.user.username == alum.Unidad.Tutor.UsuarioDjango.username (ajustar según tu modelo)


    # Si no es tutor ni jefatura, redirigir a la página previa o a homepage
    if not (es_tutor or es_jefatura):
        # Intentar redirigir a la página anterior, o "/" si no hay referrer
        return redirect(request.META.get('HTTP_REFERER', '/'))


    curso_academico_actual = get_current_academic_year()

    # Filtrar las amonestaciones y sanciones del curso académico actual
    amon_actual = Amonestaciones.objects.filter(IdAlumno_id=alum_id, curso_academico=curso_academico_actual).order_by(
        'Fecha')
    amon_vigentes = [a for a in amon_actual if a.vigente]

    historial_actual = amon_vigentes

    tipo_actual = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_actual]
    hist_actual = zip(historial_actual, tipo_actual, range(1, len(historial_actual) + 1))

    prof = True if prof == "" else False
    context = {
        'prof': prof,
        'alum': alum,
        'historial_actual': hist_actual,
        'menu_convivencia': True,
        'horas': horas,
    }

    return render(request, 'historial_vigente.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def ignorar_propuesta_sancion(request, prop_id):
    propuesta = PropuestasSancion.objects.get(pk=prop_id)
    propuesta.ignorar = True
    propuesta.save()
    return redirect('alumnadosancionable', ver_ignorados='False')

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def reactivar_propuesta_sancion(request, prop_id):
    propuesta = PropuestasSancion.objects.get(pk=prop_id)
    propuesta.ignorar = False
    propuesta.save()
    return redirect('alumnadosancionable', ver_ignorados='True')

@login_required(login_url='/')
@user_passes_test(group_check_prof_and_tutor_or_je, login_url='/')
def historial_sanciones(request, alum_id):
    curso_academico_actual = get_current_academic_year()
    alumno = get_object_or_404(Alumnos, id=alum_id)
    sanciones = Sanciones.objects.filter(
        IdAlumno=alumno, curso_academico=curso_academico_actual
    ).order_by('-Fecha')
    return render(request, 'historial_sanciones.html', {'alumno': alumno, 'sanciones': sanciones})


def crear_intervencion_horizonte(request):
    if request.method == "POST":
        form = IntervencionAulaHorizonteForm(request.POST)
        if form.is_valid():
            intervencion = form.save(commit=False)
            intervencion.profesor_atiende = request.user.profesor
            intervencion.creada_por = request.user.profesor
            intervencion.curso_academico = get_current_academic_year()
            intervencion.save()
            return redirect('listado_intervenciones_horizonte')  # o a donde prefieras
    else:
        form = IntervencionAulaHorizonteForm()

    return render(request, 'intervencion-horizonte.html', {
        'form': form,
        'profesor': request.user.profesor
    })

def listado_intervenciones_horizonte(request):
    curso_actual = get_current_academic_year()

    intervenciones = (
        IntervencionAulaHorizonte.objects
        .filter(curso_academico=curso_actual)
        .select_related('alumno', 'alumno__Unidad', 'profesor_envia', 'profesor_atiende')
        .order_by('-fecha')
    )

    profesores = Profesores.objects.filter(Baja=False)
    cursos = Cursos.objects.all()

    return render(request, 'listado_intervenciones_horizonte.html', {
        'intervenciones': intervenciones,
        'curso': curso_actual,
        'profesores': profesores,
        'cursos': cursos,
    })


@require_POST
def eliminar_intervencion_horizonte(request):

    intervencion_id = request.POST.get('id')

    if intervencion_id:
        try:
            intervencion = IntervencionAulaHorizonte.objects.get(pk=intervencion_id)
            intervencion.delete()
            return JsonResponse({'success': True})
        except IntervencionAulaHorizonte.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No encontrada'})
    return JsonResponse({'success': False, 'error': 'ID inválido'})


class IntervencionDetalleView(DetailView):
    model = IntervencionAulaHorizonte
    template_name = 'detalle_intervencion_horizonte.html'
    context_object_name = 'intervencion'


def listado_derivaciones_aula_horizonte(request):
    curso_actual = get_current_academic_year()

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

    profesores = Profesores.objects.filter(Baja=False)
    cursos = Cursos.objects.all()

    return render(request, 'listado_derivaciones_horizonte.html', {
        'amonestaciones': amonestaciones,
        'profesores': profesores,
        'cursos': cursos,
    })

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def busq_amonestaciones(request):


    horas = ["1ª hora", "2ª hora", "3ª hora", "Recreo", "4ª hora", "5ª hora", "6ª hora"]


    curso_academico_actual = get_current_academic_year()

    # Filtrar las amonestaciones y sanciones del curso académico actual
    amon_actual = Amonestaciones.objects.filter(curso_academico=curso_academico_actual).order_by(
        'Fecha')[:20]


    historial_actual = list(amon_actual)
    historial_actual = sorted(historial_actual, key=lambda x: x.Fecha, reverse=False)

    tipo_actual = ["Amonestación" if isinstance(h, Amonestaciones) else "Sanción" for h in historial_actual]
    hist_actual = zip(historial_actual, tipo_actual, range(1, len(historial_actual) + 1))

    profesores = Profesores.objects.filter(Baja=False)
    cursos = Cursos.objects.all()


    context = {
        'historial_actual': hist_actual,
        'menu_convivencia': True,
        'horas': horas,
        'profesores': profesores,
        'cursos': cursos,
    }

    return render(request, 'busq_amonestaciones.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def historico_sanciones(request):
    curso_academico_id = request.GET.get('curso_academico')
    unidad_id = request.GET.get('unidad')
    trimestre = request.GET.get('trimestre')  # '', '1', '2', '3'

    # Filtrar amonestaciones históricas
    qs = Sanciones.objects.select_related(
        'IdAlumno', 'IdAlumno__Unidad'
    ).order_by('-Fecha')

    if curso_academico_id:
        qs = qs.filter(curso_academico_id=curso_academico_id)

        # Cálculo de fechas de inicio/fin según trimestre
        if trimestre in ['1', '2', '3']:
            # Suponiendo que CursoAcademico tiene campos inicio_curso y fin_curso
            curso = CursoAcademico.objects.get(id=curso_academico_id)
            year_inicio = curso.año_inicio  # p.ej. 2024
            # 1 de septiembre siempre del año de inicio del curso
            if trimestre == '1':
                start = date(year_inicio, 9, 1)
                end = date(year_inicio, 12, 31)
            elif trimestre == '2':
                # 1 enero–31 marzo del año siguiente
                start = date(year_inicio + 1, 1, 1)
                end = date(year_inicio + 1, 3, 31)
            elif trimestre == '3':
                # 1 abril–30 junio del año siguiente
                start = date(year_inicio + 1, 4, 1)
                end = date(year_inicio + 1, 6, 30)

            qs = qs.filter(Fecha__range=(start, end))
    if unidad_id:
        qs = qs.filter(IdAlumno__Unidad_id=unidad_id)

    amonestaciones = list(qs)
    datos = zip(range(1, len(amonestaciones) + 1), amonestaciones)

    context = {
        'amonestaciones': datos,
        'cursos_academicos': CursoAcademico.objects.all().order_by('-id'),
        'unidades': Cursos.objects.all().order_by('Curso'),  # ajusta modelo
        'curso_academico_selected': curso_academico_id,
        'unidad_selected': unidad_id,
        'trimestre_selected': trimestre,
        'menu_sanciones': True,
        'menu_convivencia': True,
    }

    return render(request, 'historicosanciones.html', context)