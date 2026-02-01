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
from datetime import datetime, timedelta, date


from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django_weasyprint import WeasyTemplateResponseMixin
from django.views.generic import TemplateView

from centro.views import group_check_je
from centro.models import InfoAlumnos, Centros

from .forms import AnalisisResultados, AnalisisResultadosPorCentros1ESO, AnalisisResultadosPorCentrosESO
from centro.models import Niveles
from centro.utils import get_current_academic_year
from convivencia.models import Amonestaciones, Sanciones
from absentismo.models import ProtocoloAbs

from .indicadores import EstimacionPromocion, EficaciaTransito, EvaluacionPositivaTodo, IdoneidadCursoEdad, \
    AbandonoEscolar, Modalidad, Serie, SerieManual, SerieConvivencia
from.models import Calificaciones, IndicadoresAlumnado

# Número de cursos para hacer el análisis
NRO_CURSOS = 4

def calcular_resultados_analisis(curso_academico, convocatoria):
    # Obtener todos los niveles de una sola vez
    niveles_dict = {nivel.Abr: nivel for nivel in Niveles.objects.filter(
        Abr__in=[
            "1º ESO", "2º ESO", "3º ESO", "4º ESO",
            "1º BTO CyT", "1º BTO HyCS", "1º BTO", "2º BTO CyT", "2º BTO HyCS", "2º BTO",
            "1º SMR", "2º SMR", "1º ASIR", "2º ASIR"
        ]
    )}

    # Agrupación de niveles para facilitar cálculos
    ESO = [niveles_dict.get(f"{i}º ESO") for i in range(1, 5)]
    BTO_1 = [niveles_dict.get("1º BTO CyT"), niveles_dict.get("1º BTO HyCS")]
    BTO_2 = [niveles_dict.get("2º BTO CyT"), niveles_dict.get("2º BTO HyCS")]
    SMR = [niveles_dict.get("1º SMR"), niveles_dict.get("2º SMR")]
    ASIR = [niveles_dict.get("1º ASIR"), niveles_dict.get("2º ASIR")]

    BTO = [BTO_1, BTO_2]
    FP = []
    FP.extend(SMR)
    FP.extend(ASIR)
    niveles = []
    niveles.extend(ESO)
    niveles.extend(BTO)
    niveles.extend(FP)

    calculos = defaultdict(list)

    

    for nivel in FP:
        calculos[nivel.Nombre].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EstimacionPromocion',
                        titulo='Estimación de la promoción'
                    )
            }
        )

    for nivel in ESO:
        calculos[nivel.Nombre].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EstimacionPromocion',
                        abandono_cuenta=True,
                        titulo='Estimación de la promoción'
                    )
            }
        )
        if nivel.Nombre == "4º ESO":
            modalidades = ["PDC", "PROF", "ACAD HyCS", "ACAD CyT"]
            calculos['4º ESO'].append(
                {
                    'Estimación de la promoción (por itinerarios)':
                        Serie(
                            curso_academico, NRO_CURSOS, convocatoria, [nivel], modalidades=modalidades,
                            indicador='EstimacionPromocion', titulo='Estimación de la promoción (por itinerarios)'
                        )
                }
            )
        if nivel.Nombre == '1º ESO':
            calculos['1º ESO'].append(
                {
                    'Eficacia del tránsito':
                        Serie(
                            curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EficaciaTransito',
                            abandono_cuenta=True,
                            titulo='Eficacia del tránsito'
                        )
                }
            )
        calculos[nivel.Nombre].append(
            {
                'Alumnado con eval. positiva en todas las materias':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EvaluacionPositivaTodo',
                        abandono_cuenta=True,
                        titulo='Alumnado con eval. positiva en todas las materias'
                    )
            }
        )
        calculos[nivel.Nombre].append(
            {
                'Eficacia de la repetición':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EficaciaRepeticion',
                        abandono_cuenta=True,
                        titulo='Eficacia de la repetición'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Idoneidad curso-edad':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='IdoneidadCursoEdad',
                        abandono_cuenta=True,
                        titulo='Idoneidad curso-edad'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Abandono escolar en ESO':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='AbandonoEscolar',
                        titulo='Abandono escolar en ESO'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Amonestaciones (por cada 100 alumnos)':
                    SerieConvivencia(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], 'amonestaciones',
                        'Amonestaciones (por cada 100 alumnos)'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Sanciones (por cada 100 alumnos)':
                    SerieConvivencia(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], 'sanciones',
                        'Sanciones (por cada 100 alumnos)'
                    )
            }
        )

    modalidades = ['CyT', 'HyCS']
    for i, nivel in enumerate(BTO):
        calculos[f'{i + 1}º BTO'].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, nivel, indicador='EstimacionPromocion',
                        titulo='Estimación de la promoción'
                    )
            }
        )
        calculos[f'{i + 1}º BTO'].append(
            {
                'Estimación de la promoción (por modalidad)':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, nivel, modalidades=modalidades,
                        indicador='EstimacionPromocion', titulo='Estimación de la promoción (por modalidad)'
                    )
            }
        )



    resultados = [[nivel, []] for nivel in calculos]

    for calc_nivel in resultados:
        nivel = calc_nivel[0]
        for calculo in calculos[nivel]:
            indicador, serie = list(calculo.items())[0]
            serie.calcular()
            if serie.modalidades:
                resultado = [
                    (curso, [(modalidad, serie.resultados[curso][modalidad]) for modalidad in serie.modalidades]) for
                    curso in serie.cursos]
                calc_nivel[1].append(
                    (
                        indicador,
                        resultado,
                        serie.modalidades,
                        serie.abandono_cuenta,
                        [serie.mu[modalidad] for modalidad in serie.modalidades],
                        [serie.sigma[modalidad] for modalidad in serie.modalidades],
                        # 'grafica'
                        serie.grafica()
                    )
                )
            else:
                resultado = [(curso, serie.resultados[curso]) for curso in serie.cursos]
                calc_nivel[1].append(
                    (
                        indicador,
                        resultado,
                        serie.modalidades,
                        serie.abandono_cuenta,
                        serie.mu,
                        serie.sigma,
                        # 'grafica'
                        serie.grafica()
                    )
                )
    return resultados
@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def analisis(request):
    if request.method == 'POST':
        form = AnalisisResultados(request.POST, request.FILES)
        if form.is_valid():
            convocatoria = form.cleaned_data['Convocatoria']
            curso_academico_actual = get_current_academic_year()

            resultados = calcular_resultados_analisis(curso_academico_actual, convocatoria)

            context = {
                'form': form,
                'menu_analisis': True,
                'resultados': resultados,
                'descarga': f"/analres/analisis_pdf/?convocatoria={convocatoria}"
            }
        else:
            context = {'form': form, 'menu_analisis': True}
    else:
        form = AnalisisResultados()
        context = {'form': form, 'menu_analisis': True}

    return render(request, 'analisis.html', context)

def obtener_calificaciones(curso_academico, convocatoria):
    calificaciones = Calificaciones.objects.filter(
        curso_academico=curso_academico,
        Convocatoria=convocatoria
    ).all()

    # Crear un diccionario donde la clave es el alumno y el valor es una lista de sus calificaciones
    resultado = defaultdict(list)

    for calificacion in calificaciones:
        resultado[calificacion.Alumno].append(calificacion)

    return resultado

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def recalcular_indicadores(request):
    if request.method == 'POST':
        convocatoria = request.POST.get('Convocatoria')
        curso_academico_actual = get_current_academic_year()

        cursos = [curso_academico_actual - i for i in range(NRO_CURSOS)]
        estimacion_promocion = EstimacionPromocion()
        eficacia_transito = EficaciaTransito()
        eval_positiva_todo = EvaluacionPositivaTodo()
        idoneidad_curso_edad = IdoneidadCursoEdad()
        abandono_escolar = AbandonoEscolar()
        modalidad = Modalidad()

        for curso in cursos:
            # Cargar las calificaciones del alumnado
            calificaciones = obtener_calificaciones(curso, convocatoria)
            for alumno in calificaciones:
                info_alumno = InfoAlumnos.objects.filter(curso_academico=curso, Alumno=alumno).first()
                if not info_alumno:
                    print(f"No se encuentra info adicional de {alumno.Nombre} en {curso}.")
                    continue

                indicadores, _ = IndicadoresAlumnado.objects.get_or_create(
                    curso_academico=curso,
                    Alumno=alumno,
                    Convocatoria=convocatoria,
                    defaults={
                        'EstimacionPromocion': None,
                        'EficaciaTransito': None,
                        'EvaluacionPositivaTodo': None,
                        'EficaciaRepeticion': None,
                        'IdoneidadCursoEdad': None,
                        'AbandonoEscolar': None
                    }
                )
                indicadores.EstimacionPromocion = estimacion_promocion.calcular(calificaciones[alumno], nivel=info_alumno.Nivel)
                if info_alumno.Nivel.Abr == "1º ESO":
                    indicadores.EficaciaTransito = eficacia_transito.calcular(calificaciones[alumno])
                if "ESO" in info_alumno.Nivel.Abr:
                    indicadores.EvaluacionPositivaTodo = eval_positiva_todo.calcular(calificaciones[alumno])
                    if info_alumno.Repetidor:
                        indicadores.EficaciaRepeticion = indicadores.EstimacionPromocion
                    indicadores.IdoneidadCursoEdad = idoneidad_curso_edad.calcular(
                        calificaciones[alumno], nivel=info_alumno.Nivel, edad=info_alumno.Edad)
                    indicadores.AbandonoEscolar = abandono_escolar.calcular(calificaciones[alumno])
                if info_alumno.Nivel.Abr == "4º ESO" or "BTO" in info_alumno.Nivel.Abr:
                    mod = modalidad.calcular(calificaciones[alumno], nivel=info_alumno.Nivel)
                    indicadores.Modalidad = modalidad.calcular(calificaciones[alumno], nivel=info_alumno.Nivel)
                indicadores.save()



        return JsonResponse({'status': 'success'})

@method_decorator(login_required(login_url='/'), name='dispatch')
@method_decorator(user_passes_test(group_check_je, login_url='/'), name='dispatch')
class GenerarPDFView(WeasyTemplateResponseMixin, TemplateView):
    convocatorias = {
        'EVI': 'Evaluación inicial',
        '1EV': '1ª Evaluación',
        '2EV': '2ª Evaluacion',
        '3EV': '3ª Evaluacion',
        'FFP': 'Final FP',
        'Ord': 'Ordinaria',
        'Ext': 'Extraordinaria'
    }
    template_name = 'analisis_pdf.html'
    pdf_stylesheets = [
        # 'static/css/estilo_pdf.css',  # Define tu CSS para dar formato al PDF
        'static/plugins/bootstrap/bootstrap.min.css'
    ]
    pdf_attachment = False  # Cambiar a False si quieres visualizar el PDF en lugar de descargarlo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_academico_actual = get_current_academic_year()
        convocatoria = self.request.GET.get('convocatoria')
        resultados = calcular_resultados_analisis(curso_academico_actual, convocatoria)

        context['resultados'] = resultados
        context['curso_academico'] = curso_academico_actual.nombre
        context['convocatoria'] = self.convocatorias[convocatoria]
        return context


def calcular_domingo_de_ramos(anio):
    """
    Calcula la fecha del Domingo de Ramos para un año dado.
    El Domingo de Ramos es el domingo anterior al Domingo de Pascua.

    :param anio: Año en formato entero.
    :return: Fecha del Domingo de Ramos como un objeto datetime.date.
    """
    # Cálculo del Domingo de Pascua utilizando el algoritmo de computus
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1

    # Fecha del Domingo de Pascua
    domingo_pascua = date(anio, mes, dia)

    # Fecha del Domingo de Ramos (una semana antes)
    domingo_ramos = domingo_pascua - timedelta(days=7)
    return domingo_ramos


def calcular_amonestaciones_1_ESO_por_centro(curso_academico, convocatoria, centro):
    if convocatoria == "1EV":
        fecha_inicio = datetime.strptime(f'01/09/{curso_academico.año_inicio}', '%d/%m/%Y')
        fecha_fin = datetime.strptime(f'23/12/{curso_academico.año_inicio}', '%d/%m/%Y')
    elif convocatoria == "2EV":
        fecha_inicio = datetime.strptime(f'07/01/{curso_academico.año_fin}', '%d/%m/%Y')
        fecha_fin = calcular_domingo_de_ramos(curso_academico.año_fin)
    else:
        fecha_inicio = calcular_domingo_de_ramos(curso_academico.año_fin)
        fecha_fin = datetime.strptime(f'30/06/{curso_academico.año_fin}', '%d/%m/%Y')

    datos = Amonestaciones.objects.filter(
        curso_academico=curso_academico,
        Fecha__range=(fecha_inicio, fecha_fin),
        IdAlumno__info_adicional__Nivel__Abr="1º ESO",
        IdAlumno__info_adicional__curso_academico=curso_academico,
    )

    total = datos.count()
    parte = datos.filter(
        IdAlumno__info_adicional__CentroOrigen=centro
    ).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0




def calcular_amonestaciones_ESO_por_centro(curso_academico, curso, convocatoria, centro):
    if convocatoria == "1EV":
        fecha_inicio = datetime.strptime(f'01/09/{curso_academico.año_inicio}', '%d/%m/%Y')
        fecha_fin = datetime.strptime(f'23/12/{curso_academico.año_inicio}', '%d/%m/%Y')
    elif convocatoria == "2EV":
        fecha_inicio = datetime.strptime(f'07/01/{curso_academico.año_fin}', '%d/%m/%Y')
        fecha_fin = calcular_domingo_de_ramos(curso_academico.año_fin)
    else:
        fecha_inicio = calcular_domingo_de_ramos(curso_academico.año_fin)
        fecha_fin = datetime.strptime(f'30/06/{curso_academico.año_fin}', '%d/%m/%Y')

    datos = Amonestaciones.objects.filter(
        curso_academico=curso_academico,
        Fecha__range=(fecha_inicio, fecha_fin),
        IdAlumno__info_adicional__Nivel__Abr=curso,
        IdAlumno__info_adicional__curso_academico=curso_academico,
    )

    total = datos.count()
    parte = datos.filter(
        IdAlumno__Centro_EP=centro
    ).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0





def calcular_sanciones_1_ESO_por_centro(curso_academico, convocatoria, centro):
    if convocatoria == "1EV":
        fecha_inicio = datetime.strptime(f'01/09/{curso_academico.año_inicio}', '%d/%m/%Y')
        fecha_fin = datetime.strptime(f'23/12/{curso_academico.año_inicio}', '%d/%m/%Y')
    elif convocatoria == "2EV":
        fecha_inicio = datetime.strptime(f'07/01/{curso_academico.año_fin}', '%d/%m/%Y')
        fecha_fin = calcular_domingo_de_ramos(curso_academico.año_fin)
    else:
        fecha_inicio = calcular_domingo_de_ramos(curso_academico.año_fin)
        fecha_fin = datetime.strptime(f'30/06/{curso_academico.año_fin}', '%d/%m/%Y')

    datos = Sanciones.objects.filter(
        curso_academico=curso_academico,
        Fecha__range=(fecha_inicio, fecha_fin),
        IdAlumno__info_adicional__Nivel__Abr="1º ESO",
        IdAlumno__info_adicional__curso_academico=curso_academico,
    )

    total = datos.count()
    parte = datos.filter(
        IdAlumno__info_adicional__CentroOrigen=centro
    ).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0




def calcular_sanciones_ESO_por_centro(curso_academico, curso, convocatoria, centro):
    if convocatoria == "1EV":
        fecha_inicio = datetime.strptime(f'01/09/{curso_academico.año_inicio}', '%d/%m/%Y')
        fecha_fin = datetime.strptime(f'23/12/{curso_academico.año_inicio}', '%d/%m/%Y')
    elif convocatoria == "2EV":
        fecha_inicio = datetime.strptime(f'07/01/{curso_academico.año_fin}', '%d/%m/%Y')
        fecha_fin = calcular_domingo_de_ramos(curso_academico.año_fin)
    else:
        fecha_inicio = calcular_domingo_de_ramos(curso_academico.año_fin)
        fecha_fin = datetime.strptime(f'30/06/{curso_academico.año_fin}', '%d/%m/%Y')

    datos = Sanciones.objects.filter(
        curso_academico=curso_academico,
        Fecha__range=(fecha_inicio, fecha_fin),
        IdAlumno__info_adicional__Nivel__Abr=curso,
        IdAlumno__info_adicional__curso_academico=curso_academico,
    )

    total = datos.count()
    parte = datos.filter(
        IdAlumno__Centro_EP=centro
    ).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0



def calcular_absentismo_1_ESO_por_centro(curso_academico, convocatoria, centro):
    if convocatoria == "1EV":
        fecha_inicio = datetime.strptime(f'01/09/{curso_academico.año_inicio}', '%d/%m/%Y')
        fecha_fin = datetime.strptime(f'23/12/{curso_academico.año_inicio}', '%d/%m/%Y')
    elif convocatoria == "2EV":
        fecha_inicio = datetime.strptime(f'07/01/{curso_academico.año_fin}', '%d/%m/%Y')
        fecha_fin = calcular_domingo_de_ramos(curso_academico.año_fin)
    else:
        fecha_inicio = calcular_domingo_de_ramos(curso_academico.año_fin)
        fecha_fin = datetime.strptime(f'30/06/{curso_academico.año_fin}', '%d/%m/%Y')

    datos = ProtocoloAbs.objects.filter(
        curso_academico=curso_academico,
        abierto=True,
        alumno__info_adicional__Nivel__Abr="1º ESO",
        alumno__info_adicional__curso_academico=curso_academico,
        fecha_apertura__range=(fecha_inicio, fecha_fin),
    )


    total = datos.count()

    parte = datos.filter(
        alumno__info_adicional__CentroOrigen=centro
    ).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0

def calcular_indicador_1_ESO_por_centro(curso_academico, convocatoria, indicador, centro=None):
    if centro:
        datos = IndicadoresAlumnado.objects.filter(
            curso_academico=curso_academico,
            Convocatoria=convocatoria,
            Alumno__info_adicional__curso_academico=curso_academico,
            Alumno__info_adicional__Nivel__Abr="1º ESO",
            Alumno__info_adicional__CentroOrigen=centro
        )
    else:
        datos = IndicadoresAlumnado.objects.filter(
            curso_academico=curso_academico,
            Convocatoria=convocatoria,
            Alumno__info_adicional__curso_academico=curso_academico,
            Alumno__info_adicional__Nivel__Abr="1º ESO",
        )

    datos.exclude(**{indicador: None})
    total = datos.count()
    parte = datos.filter(**{indicador: True}).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0



def calcular_indicador_ESO_por_centro(curso_academico, curso, convocatoria, indicador, centro=None):
    if centro:
        datos = IndicadoresAlumnado.objects.filter(
            curso_academico=curso_academico,
            Convocatoria=convocatoria,
            Alumno__info_adicional__curso_academico=curso_academico,
            Alumno__info_adicional__Nivel__Abr=curso,
            Alumno__Centro_EP=centro
        )
    else:
        datos = IndicadoresAlumnado.objects.filter(
            curso_academico=curso_academico,
            Convocatoria=convocatoria,
            Alumno__info_adicional__curso_academico=curso_academico,
            Alumno__info_adicional__Nivel__Abr=curso,
        )

    datos.exclude(**{indicador: None})
    total = datos.count()
    parte = datos.filter(**{indicador: True}).count()

    if total > 0:
        return 100 * parte / total
    else:
        return 0



def calcular_resultados_analisis_ESO_por_centros(curso_academico, curso, convocatoria, centros):
    indicadores = [
        'EstimacionPromocion',
        'EficaciaTransito',
        'EficaciaRepeticion',
        'EvaluacionPositivaTodo',
        'AbandonoEscolar',
    ]

    titulos = {
        'EstimacionPromocion': 'Estimación de la promoción',
        'EficaciaTransito': 'Eficacia del tránsito',
        'EficaciaRepeticion': 'Eficacia de la repetición',
        'EvaluacionPositivaTodo': 'Evaluación positiva en todas las materias',
        'AbandonoEscolar': 'Abandono Escolar',
    }

    if curso != "1º ESO":
        indicadores.remove('EficaciaTransito')
        del titulos['EficaciaTransito']

    calculos = {
        indicador: {
            centro.Nombre: calcular_indicador_ESO_por_centro(
                curso_academico, curso, convocatoria, indicador, centro
            ) for centro in centros
        } for indicador in indicadores
    }

    for indicador in indicadores:
        calculos[indicador]['IES Gonzalo Nazareno'] = calcular_indicador_ESO_por_centro(
            curso_academico, curso, convocatoria, indicador
        )

    nombres_centro = [centro.Nombre for centro in centros]

    series = {
        indicador: SerieManual(
            nombres_centro, calculos[indicador], calculos[indicador]['IES Gonzalo Nazareno'], titulos[indicador]
        ) for indicador in indicadores
    }

    indicadores.append('Amonestaciones')
    titulos['Amonestaciones'] = 'Amonestaciones (%)'
    calculos['Amonestaciones'] = {
        centro.Nombre: calcular_amonestaciones_ESO_por_centro(curso_academico, curso, convocatoria, centro)
        for centro in centros
    }

    series['Amonestaciones'] = SerieManual(
        nombres_centro, calculos['Amonestaciones'], None, titulos['Amonestaciones']
    )

    indicadores.append('Sanciones')
    titulos['Sanciones'] = 'Sanciones (%)'
    calculos['Sanciones'] = {
        centro.Nombre: calcular_sanciones_ESO_por_centro(curso_academico, curso, convocatoria, centro)
        for centro in centros
    }

    series['Sanciones'] = SerieManual(
        nombres_centro, calculos['Sanciones'], None, titulos['Sanciones']
    )

    resultados = [(titulos[indicador], list(series[indicador].valores.items()), series[indicador].grafica()) for indicador in indicadores]
    return resultados

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def analisis_por_centros_1_ESO(request):
    if request.method == 'POST':
        form = AnalisisResultadosPorCentros1ESO(request.POST)

        if form.is_valid():
            curso_academico_actual = get_current_academic_year()
            convocatoria = form.cleaned_data['Convocatoria']
            centros_id = form.cleaned_data['Centros']
            centros = [Centros.objects.get(id=i) for i in centros_id]
            resultados = calcular_resultados_analisis_1_ESO_por_centros(curso_academico_actual, convocatoria, centros)
            centros_ids = ",".join(centros_id)
            context = {
                'form': form,
                'resultados': resultados,
                'descarga': f"/analres/analisis_1ESO_pdf/?convocatoria={convocatoria}&centros={centros_ids}",
                'menu_analisis': True}
    else:
        form = AnalisisResultadosPorCentros1ESO()
        context = {'form': form, 'menu_analisis': True}

    return render(request, 'analisis_por_centros_1_ESO.html', context)


def calcular_resultados_analisis_1_ESO_por_centros(curso_academico, convocatoria, centros):
    indicadores = [
        'EstimacionPromocion',
        'EficaciaTransito',
        'EvaluacionPositivaTodo',
        'AbandonoEscolar',
    ]
    titulos = {
        'EstimacionPromocion': 'Estimación de la promoción',
        'EficaciaTransito': 'Eficacia del tránsito',
        'EvaluacionPositivaTodo': 'Evaluación positiva en todas las materias',
        'AbandonoEscolar': 'Abandono Escolar',
    }
    calculos = {
        indicador: {
            centro.Nombre: calcular_indicador_1_ESO_por_centro(
                curso_academico, convocatoria, indicador, centro
            ) for centro in centros
        } for indicador in indicadores
    }

    for indicador in indicadores:
        calculos[indicador]['IES Gonzalo Nazareno'] = calcular_indicador_1_ESO_por_centro(
            curso_academico, convocatoria, indicador
        )

    nombres_centro = [centro.Nombre for centro in centros]

    series = {
        indicador: SerieManual(
            nombres_centro, calculos[indicador], calculos[indicador]['IES Gonzalo Nazareno'], titulos[indicador]
        ) for indicador in indicadores
    }

    indicadores.append('Amonestaciones')
    titulos['Amonestaciones'] = 'Amonestaciones (%)'
    calculos['Amonestaciones'] = {
        centro.Nombre: calcular_amonestaciones_1_ESO_por_centro(curso_academico, convocatoria, centro)
        for centro in centros
    }

    series['Amonestaciones'] = SerieManual(
        nombres_centro, calculos['Amonestaciones'], None, titulos['Amonestaciones']
    )

    indicadores.append('Sanciones')
    titulos['Sanciones'] = 'Sanciones (%)'
    calculos['Sanciones'] = {
        centro.Nombre: calcular_sanciones_1_ESO_por_centro(curso_academico, convocatoria, centro)
        for centro in centros
    }

    series['Sanciones'] = SerieManual(
        nombres_centro, calculos['Sanciones'], None, titulos['Sanciones']
    )

    resultados = [(titulos[indicador], list(series[indicador].valores.items()), series[indicador].grafica()) for indicador in indicadores]
    return resultados


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def analisis_por_centros_ESO(request):
    if request.method == 'POST':
        form = AnalisisResultadosPorCentrosESO(request.POST)

        if form.is_valid():
            curso_academico_actual = get_current_academic_year()
            convocatoria = form.cleaned_data['Convocatoria']
            cursos = form.cleaned_data['Cursos']
            centros_id = form.cleaned_data['Centros']
            centros = [Centros.objects.get(id=i) for i in centros_id]
            resultados = (
                (curso, calcular_resultados_analisis_ESO_por_centros(
                    curso_academico_actual, curso, convocatoria, centros
                )) for curso in cursos
            )
            centros_ids = ",".join(centros_id)
            cursos_ids = ",".join([curso[0] for curso in cursos])
            context = {
                'form': form,
                'resultados': resultados,
                'cursos': cursos,
                'descarga': f"/analres/analisis_ESO_pdf/?convocatoria={convocatoria}&cursos={cursos_ids}&centros={centros_ids}",
                'menu_analisis': True}
    else:
        form = AnalisisResultadosPorCentrosESO()
        context = {'form': form, 'menu_analisis': True}

    return render(request, 'analisis_por_centros_ESO.html', context)




@method_decorator(login_required(login_url='/'), name='dispatch')
@method_decorator(user_passes_test(group_check_je, login_url='/'), name='dispatch')
class GenerarPDF1ESOView(WeasyTemplateResponseMixin, TemplateView):
    convocatorias = {
        '1EV': '1ª Evaluación',
        '2EV': '2ª Evaluacion',
        'Ord': 'Ordinaria',
    }
    template_name = 'analisis_1ESO_pdf.html'
    pdf_stylesheets = [
        # 'static/css/estilo_pdf.css',  # Define tu CSS para dar formato al PDF
        'static/plugins/bootstrap/bootstrap.min.css'
    ]
    pdf_attachment = False  # Cambiar a False si quieres visualizar el PDF en lugar de descargarlo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_academico_actual = get_current_academic_year()
        convocatoria = self.request.GET.get('convocatoria')
        centros_ids = self.request.GET.get('centros')
        centros_id = [int(i) for i in centros_ids.split(',')]
        centros = [Centros.objects.get(id=int(i)) for i in centros_id]
        resultados = calcular_resultados_analisis_1_ESO_por_centros(curso_academico_actual, convocatoria, centros)

        context['resultados'] = resultados
        context['curso_academico'] = curso_academico_actual.nombre
        context['convocatoria'] = self.convocatorias[convocatoria]
        return context

@method_decorator(login_required(login_url='/'), name='dispatch')
@method_decorator(user_passes_test(group_check_je, login_url='/'), name='dispatch')
class GenerarPDFESOView(WeasyTemplateResponseMixin, TemplateView):
    convocatorias = {
        '1EV': '1ª Evaluación',
        '2EV': '2ª Evaluacion',
        'Ord': 'Ordinaria',
    }
    template_name = 'analisis_ESO_pdf.html'
    pdf_stylesheets = [
        # 'static/css/estilo_pdf.css',  # Define tu CSS para dar formato al PDF
        'static/plugins/bootstrap/bootstrap.min.css'
    ]
    pdf_attachment = False  # Cambiar a False si quieres visualizar el PDF en lugar de descargarlo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_academico_actual = get_current_academic_year()
        convocatoria = self.request.GET.get('convocatoria')
        centros_ids = self.request.GET.get('centros')
        centros_id = [int(i) for i in centros_ids.split(',')]
        centros = [Centros.objects.get(id=int(i)) for i in centros_id]
        cursos_ids = self.request.GET.get('cursos')
        cursos_id = [int(i) for i in cursos_ids.split(',')]
        cursos = [f'{curso}º ESO' for curso in cursos_id]
        resultados = [
            (curso, calcular_resultados_analisis_ESO_por_centros(
                curso_academico_actual, curso, convocatoria, centros
            )) for curso in cursos
        ]

        context['resultados'] = resultados
        context['curso_academico'] = curso_academico_actual.nombre
        context['convocatoria'] = self.convocatorias[convocatoria]
        context['cursos'] = cursos
        return context


def analisis_historico_por_centros_ESO(request):
    """
    Vista para mostrar la evolución histórica de un nivel específico (ej. 1º ESO)
    filtrando alumnos por su centro de procedencia.
    """
    curso_academico_actual = get_current_academic_year()
    resultados = []
    nivel_str = ""
    centros_str = ""

    if request.method == 'POST':
        form = AnalisisResultadosPorCentrosESO(request.POST)
        if form.is_valid():
            convocatoria = form.cleaned_data['Convocatoria']
            # Asumimos que el form devuelve una lista de IDs de cursos (niveles)
            # Para la serie temporal, es mejor analizar un nivel concreto a la vez o agregarlos.
            # Aquí tomaremos el primer nivel seleccionado para hacer la serie.
            cursos_seleccionados = form.cleaned_data['Cursos']
            centros_seleccionados = form.cleaned_data['Centros']
            centros_id = [int(c) for c in centros_seleccionados]

            # Convertimos inputs a objetos
            centros_objs = list(Centros.objects.filter(id__in=centros_id).all())
            centros_str = ", ".join([c.Nombre for c in centros_objs])

            # Si el usuario selecciona varios cursos (ej 1ESO, 2ESO), iteramos o agrupamos.
            # Para este ejemplo, haré una serie agregada de los niveles seleccionados
            # (ej. "Evolución de 1º ESO para alumnos del colegio X")

            # Mapeo de IDs de cursos a Niveles (model)
            # Nota: Ajusta esto según cómo tu formulario 'Cursos' devuelva los datos (si devuelve ID de nivel o string)
            # Suponiendo que devuelve strings como '1' para 1º ESO, etc.
            mapa_cursos = {
                '1': '1º ESO', '2': '2º ESO', '3': '3º ESO', '4': '4º ESO'
            }
            # Obtenemos los objetos Nivel correspondientes
            nombres_niveles = [mapa_cursos.get(c) for c in cursos_seleccionados if mapa_cursos.get(c)]
            niveles_obj = Niveles.objects.filter(Abr__in=nombres_niveles)
            nivel_str = ", ".join(nombres_niveles)

            # --- DEFINICIÓN DE LA CLASE SERIE PERSONALIZADA ---
            # Necesitamos una clase Serie que sepa filtrar por 'Centro de Origen'
            # Lo hacemos dinámicamente o podrías crearla en indicadores.py

            class SeriePorCentro(Serie):
                def calcular(self):
                    self.resultados = {curso: 0. for curso in self.cursos}
                    res_valores = []

                    for curso in self.cursos:
                        # Obtenemos calificaciones del curso y niveles
                        # PERO filtramos por alumnos que vengan de los centros seleccionados
                        calificaciones = Calificaciones.objects.filter(
                            curso_academico=curso,
                            Nivel__in=self.niveles,
                            Convocatoria=self.convocatoria,
                            Alumno__Centro__in=centros_objs  # <--- EL FILTRO CLAVE
                        )

                        # Instanciamos el indicador (ej. EstimacionPromocion)
                        indicador = self.indicador_cls()
                        # Calculamos
                        valor = indicator_calc_wrapper(indicador, calificaciones)
                        # Nota: indicator_calc_wrapper es una abstracción.
                        # En tu código real, tus indicadores (ej EstimacionPromocion) suelen tener
                        # lógica interna. Si tus indicadores esperan 'calificaciones' queryset:

                        if calificaciones.exists():
                            # Tus indicadores suelen devolver (True_count / Total) * 100
                            # Tendrás que adaptar esto según cómo 'calcular' de cada Indicador funcione.
                            # Si tus indicadores usan 'IndicadoresAlumnado' pre-calculado, el filtro cambia:
                            pass

                            # --- RE-IMPLEMENTACIÓN BASADA EN TU ARQUITECTURA ---
                    # Al ver tu indicadores.py, usas IndicadoresAlumnado o lógica directa.
                    # Vamos a usar la lógica de filtrar InfoAlumnos / IndicadoresAlumnado

            # -------------------------------------------------------------------------
            # LÓGICA DE CÁLCULO DIRECTA (Más segura con tu código actual)
            # -------------------------------------------------------------------------

            def calcular_serie_filtrada(ClaseIndicador, titulo):
                """Helper para construir la serie con filtro de centros"""
                serie = Serie(
                    curso_academico=curso_academico_actual,
                    nro_cursos=NRO_CURSOS,
                    convocatoria=convocatoria,
                    niveles=niveles_obj,
                    titulo=titulo
                )

                # Sobrescribimos el método calcular de la instancia (Monkey patching)
                # o usamos una subclase si prefieres limpieza en indicadores.py

                # Vamos a calcular manualmente los valores para inyectarlos
                datos_serie = {}
                valores_raw = []

                for curso_hist in serie.cursos:
                    # Filtramos IndicadoresAlumnado por:
                    # 1. Curso y Nivel
                    # 2. Alumno cuyo 'Centro' (origen) esté en la lista
                    qs = IndicadoresAlumnado.objects.filter(
                        curso_academico=curso_hist,
                        Nivel__in=niveles_obj,
                        IdAlumno__Centro__in=centros_objs  # Filtro por centro origen
                    )

                    total = qs.count()
                    if total > 0:
                        # Usamos el nombre del indicador para obtener el campo booleano
                        # Asumiendo que ClaseIndicador.__name__ coincide con el campo del modelo
                        nombre_campo = ClaseIndicador.__name__

                        # Filtramos los True
                        positivos = qs.filter(**{nombre_campo: True}).count()
                        valor = (positivos / total) * 100
                    else:
                        valor = 0

                    datos_serie[curso_hist] = valor
                    valores_raw.append(valor)

                # Asignamos resultados a la serie manual
                serie.resultados = datos_serie
                import statistics
                serie.mu = statistics.mean(valores_raw) if valores_raw else 0
                serie.sigma = statistics.stdev(valores_raw) if len(valores_raw) > 1 else 0

                return serie

            # --- GENERACIÓN DE INDICADORES ---

            # 1. Estimación Promoción
            s1 = calcular_serie_filtrada(EstimacionPromocion, f"Estimación Promoción ({centros_str})")
            resultados.append({'titulo': s1.titulo, 'grafica': s1.grafica(), 'mu': s1.mu, 'sigma': s1.sigma})

            # 2. Eficacia Tránsito (Solo si es 1º ESO usualmente, pero lo dejamos genérico)
            s2 = calcular_serie_filtrada(EficaciaTransito, f"Eficacia Tránsito ({centros_str})")
            resultados.append({'titulo': s2.titulo, 'grafica': s2.grafica(), 'mu': s2.mu, 'sigma': s2.sigma})

            # 3. Evaluación Positiva Todo
            s3 = calcular_serie_filtrada(EvaluacionPositivaTodo, f"Evaluación Positiva Todo ({centros_str})")
            resultados.append({'titulo': s3.titulo, 'grafica': s3.grafica(), 'mu': s3.mu, 'sigma': s3.sigma})

            # 4. Idoneidad (No depende de resultados, pero sí demográfico)
            # Idoneidad suele ser campo 'Idoneidad' en IndicadoresAlumnado?
            # Si es calculado al vuelo, usa lógica similar. Asumiré que está en modelo.
            s4 = calcular_serie_filtrada(IdoneidadCursoEdad, f"Idoneidad Curso-Edad ({centros_str})")
            resultados.append({'titulo': s4.titulo, 'grafica': s4.grafica(), 'mu': s4.mu, 'sigma': s4.sigma})

    else:
        form = AnalisisResultadosPorCentrosESO()

    return render(request, 'analisis_historico_por_centros.html', {
        'form': form,
        'resultados': resultados,
        'nivel_seleccionado': nivel_str,
        'centros_seleccionados': centros_str
    })


def calcular_resultados_analisis_por_centros(curso_academico, convocatoria, centros=None):
    # Obtener todos los niveles de una sola vez
    niveles_dict = {nivel.Abr: nivel for nivel in Niveles.objects.filter(
        Abr__in=[
            "1º ESO", "2º ESO", "3º ESO", "4º ESO",
            "1º BTO CyT", "1º BTO HyCS", "1º BTO", "2º BTO CyT", "2º BTO HyCS", "2º BTO",
            "1º SMR", "2º SMR", "1º ASIR", "2º ASIR"
        ]
    )}

    # Agrupación de niveles para facilitar cálculos
    ESO = [niveles_dict.get(f"{i}º ESO") for i in range(1, 5)]
    BTO_1 = [niveles_dict.get("1º BTO CyT"), niveles_dict.get("1º BTO HyCS")]
    BTO_2 = [niveles_dict.get("2º BTO CyT"), niveles_dict.get("2º BTO HyCS")]
    SMR = [niveles_dict.get("1º SMR"), niveles_dict.get("2º SMR")]
    ASIR = [niveles_dict.get("1º ASIR"), niveles_dict.get("2º ASIR")]

    BTO = [BTO_1, BTO_2]
    FP = []
    FP.extend(SMR)
    FP.extend(ASIR)
    niveles = []
    niveles.extend(ESO)
    niveles.extend(BTO)
    niveles.extend(FP)

    calculos = defaultdict(list)

    for nivel in FP:
        calculos[nivel.Nombre].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EstimacionPromocion',
                        titulo='Estimación de la promoción'
                    )
            }
        )

    for nivel in ESO:
        calculos[nivel.Nombre].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EstimacionPromocion',
                        abandono_cuenta=True,
                        titulo='Estimación de la promoción'
                    )
            }
        )
        if nivel.Nombre == "4º ESO":
            modalidades = ["PDC", "PROF", "ACAD HyCS", "ACAD CyT"]
            calculos['4º ESO'].append(
                {
                    'Estimación de la promoción (por itinerarios)':
                        Serie(
                            curso_academico, NRO_CURSOS, convocatoria, [nivel], modalidades=modalidades,
                            indicador='EstimacionPromocion', titulo='Estimación de la promoción (por itinerarios)'
                        )
                }
            )
        if nivel.Nombre == '1º ESO':
            calculos['1º ESO'].append(
                {
                    'Eficacia del tránsito':
                        Serie(
                            curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EficaciaTransito',
                            abandono_cuenta=True,
                            titulo='Eficacia del tránsito'
                        )
                }
            )
        calculos[nivel.Nombre].append(
            {
                'Alumnado con eval. positiva en todas las materias':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EvaluacionPositivaTodo',
                        abandono_cuenta=True,
                        titulo='Alumnado con eval. positiva en todas las materias'
                    )
            }
        )
        calculos[nivel.Nombre].append(
            {
                'Eficacia de la repetición':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='EficaciaRepeticion',
                        abandono_cuenta=True,
                        titulo='Eficacia de la repetición'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Idoneidad curso-edad':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='IdoneidadCursoEdad',
                        abandono_cuenta=True,
                        titulo='Idoneidad curso-edad'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Abandono escolar en ESO':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], indicador='AbandonoEscolar',
                        titulo='Abandono escolar en ESO'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Amonestaciones (por cada 100 alumnos)':
                    SerieConvivencia(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], 'amonestaciones',
                        'Amonestaciones (por cada 100 alumnos)'
                    )
            }
        )

        calculos[nivel.Nombre].append(
            {
                'Sanciones (por cada 100 alumnos)':
                    SerieConvivencia(
                        curso_academico, NRO_CURSOS, convocatoria, [nivel], 'sanciones',
                        'Sanciones (por cada 100 alumnos)'
                    )
            }
        )

    modalidades = ['CyT', 'HyCS']
    for i, nivel in enumerate(BTO):
        calculos[f'{i + 1}º BTO'].append(
            {
                'Estimación de la promoción':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, nivel, indicador='EstimacionPromocion',
                        titulo='Estimación de la promoción'
                    )
            }
        )
        calculos[f'{i + 1}º BTO'].append(
            {
                'Estimación de la promoción (por modalidad)':
                    Serie(
                        curso_academico, NRO_CURSOS, convocatoria, nivel, modalidades=modalidades,
                        indicador='EstimacionPromocion', titulo='Estimación de la promoción (por modalidad)'
                    )
            }
        )

    resultados = [[nivel, []] for nivel in calculos]

    for calc_nivel in resultados:
        nivel = calc_nivel[0]
        for calculo in calculos[nivel]:
            indicador, serie = list(calculo.items())[0]
            serie.calcular()
            if serie.modalidades:
                resultado = [
                    (curso, [(modalidad, serie.resultados[curso][modalidad]) for modalidad in serie.modalidades]) for
                    curso in serie.cursos]
                calc_nivel[1].append(
                    (
                        indicador,
                        resultado,
                        serie.modalidades,
                        serie.abandono_cuenta,
                        [serie.mu[modalidad] for modalidad in serie.modalidades],
                        [serie.sigma[modalidad] for modalidad in serie.modalidades],
                        # 'grafica'
                        serie.grafica()
                    )
                )
            else:
                resultado = [(curso, serie.resultados[curso]) for curso in serie.cursos]
                calc_nivel[1].append(
                    (
                        indicador,
                        resultado,
                        serie.modalidades,
                        serie.abandono_cuenta,
                        serie.mu,
                        serie.sigma,
                        # 'grafica'
                        serie.grafica()
                    )
                )
    return resultados