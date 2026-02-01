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


from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic import TemplateView, View
from django_weasyprint import WeasyTemplateResponseMixin

from .models import CampanaTransito, InformeDepartamento
from .forms import InformeDepartamentoForm, DescargarInformeForm, RendimientoDepartamentosForm, InformeHistoricoForm

from .utils import calcular_tasa_exito


@login_required
def gestion_informe_transito(request):
    # 1. Obtener campañas activas para el desplegable inicial
    # Ajusta el filtro según tu lógica de "Curso actual"
    campanas = CampanaTransito.objects.all().select_related('curso_academico')
    campanas = campanas.filter(cerrada=False).all()

    # 2. Detectar campaña seleccionada (por GET o por POST previo)
    campana_id = request.GET.get('campana_id')
    campana_seleccionada = None
    form = None

    if campana_id:
        campana_seleccionada = get_object_or_404(CampanaTransito, pk=campana_id)

    # --- PROCESAMIENTO DEL FORMULARIO (POST) ---
    if request.method == 'POST' and campana_seleccionada:
        # Recuperamos datos clave para saber si es CREACIÓN o EDICIÓN
        centro_id = request.POST.get('centro_origen')
        materia_id = request.POST.get('materia')

        # Intentamos buscar si ya existe un informe para esta combinación
        # Esto es vital para evitar el error de 'Unique Constraint'
        informe_existente = InformeDepartamento.objects.filter(
            campana=campana_seleccionada,
            centro_origen_id=centro_id,
            materia_id=materia_id
        ).first()

        # Instanciamos el form: Si existe informe, pasamos 'instance' (UPDATE), si no, es (CREATE)
        form = InformeDepartamentoForm(request.POST, instance=informe_existente, campana=campana_seleccionada, user=request.user)

        if form.is_valid():
            informe = form.save(commit=False)
            informe.campana = campana_seleccionada
            informe.save()

            messages.success(request, "Informe guardado correctamente.")
            # Redirigimos a la misma url manteniendo la campaña seleccionada
            return redirect(f"{request.path}?campana_id={campana_id}")
        else:
            messages.error(request, "Error al guardar el informe. Revisa los campos.")

    # --- CARGA INICIAL (GET) ---
    else:
        if campana_seleccionada:
            # Renderizamos formulario vacío, pero vinculado a la campaña para filtrar los selects
            form = InformeDepartamentoForm(campana=campana_seleccionada, user=request.user)

    context = {
        'campanas': campanas,
        'campana_seleccionada': campana_seleccionada,
        'form': form,
    }
    return render(request, 'informe_transito.html', context)


@login_required
def api_check_informe(request):
    """
    Vista ligera que responde a llamadas AJAX.
    Verifica si existe un informe para Campaña + Centro + Materia.
    Devuelve JSON.
    """
    campana_id = request.GET.get('campana_id')
    centro_id = request.GET.get('centro_id')
    materia_id = request.GET.get('materia_id')

    data = {'existe': False}

    if campana_id and centro_id and materia_id:
        try:
            informe = InformeDepartamento.objects.get(
                campana_id=campana_id,
                centro_origen_id=centro_id,
                materia_id=materia_id
            )
            data = {
                'existe': True,
                'cuestiones': informe.cuestiones_generales or "",
                'fortalezas': informe.fortalezas or "",
                'debilidades': informe.debilidades or ""
            }
        except InformeDepartamento.DoesNotExist:
            pass  # Devuelve existe: False

    return JsonResponse(data)


class DescargarInformePDFView(LoginRequiredMixin, UserPassesTestMixin, WeasyTemplateResponseMixin, TemplateView):
    # Plantilla para el PDF
    template_name = 'pdf_informe_global.html'
    # Nombre del archivo descarga
    pdf_filename = 'informe_transito.pdf'

    def test_func(self):
        # Solo para Jefatura de Estudios
        return self.request.user.groups.filter(name='jefatura de estudios').exists()

    def get(self, request, *args, **kwargs):
        # Renderiza el formulario de selección (NO el PDF)
        form = DescargarInformeForm()
        return render(request, 'form_descarga_pdf.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = DescargarInformeForm(data=request.POST)

        # Si el usuario pulsó el botón de "Generar PDF" y el form es válido
        if 'generar_pdf' in request.POST and form.is_valid():
            # Preparamos los datos para el PDF
            campana = form.cleaned_data['campana']
            centro = form.cleaned_data['centro']

            # Recuperamos TODAS las materias de la configuración (requisito clave)
            materias = campana.materias_implicadas.all().order_by('abr')

            lista_resultados = []
            for materia in materias:
                # Intentamos buscar el informe
                informe = InformeDepartamento.objects.filter(
                    campana=campana,
                    centro_origen=centro,
                    materia=materia
                ).first()

                # Añadimos a la lista una tupla o dict: (Materia, ObjetoInforme o None)
                lista_resultados.append({
                    'materia': materia,
                    'informe': informe  # Será None si no se rellenó
                })

            # Actualizamos el contexto para WeasyPrint
            context = self.get_context_data(**kwargs)
            context.update({
                'campana': campana,
                'centro': centro,
                'resultados': lista_resultados,
            })

            # Cambiamos el nombre del archivo dinámicamente
            self.pdf_filename = f"Informe_Transito_{centro.Nombre}_{campana.curso_academico}.pdf"

            # Renderizamos el PDF
            return self.render_to_response(context)

        # Si es un POST normal (cambio de dropdown), volvemos a mostrar el formulario refrescado
        return render(request, 'form_descarga_pdf.html', {'form': form})


class RendimientoDepartamentosPDFView(LoginRequiredMixin, UserPassesTestMixin, WeasyTemplateResponseMixin,
                                      TemplateView):
    template_name = 'pdf_rendimiento_dptos.html'
    pdf_filename = 'rendimiento_departamentos.pdf'

    def test_func(self):
        return self.request.user.groups.filter(name='jefatura de estudios').exists()

    def get(self, request, *args, **kwargs):
        # Muestra el formulario de selección
        form = RendimientoDepartamentosForm()
        return render(request, 'form_rendimiento_dptos.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = RendimientoDepartamentosForm(data=request.POST)

        # Detectamos si es el POST final de generar PDF
        if 'generar_pdf' in request.POST and form.is_valid():
            campana = form.cleaned_data['campana']
            curso = form.cleaned_data['curso']

            # 1. Recuperamos materias y centros implicados
            materias = campana.materias_implicadas.all().select_related('nivel').order_by('nivel__Nombre', 'abr')
            centros = campana.centros_origen.all().order_by('Nombre')

            datos_informe = []

            # 2. Construimos la matriz de datos
            for materia in materias:
                tasa_global = calcular_tasa_exito(curso, campana, None, materia)

                # Si la función devuelve None, es que esa asignatura no existía en ese curso
                if tasa_global is None:
                    continue  # Saltamos esta materia para este año

                filas_centros = []
                for centro in centros:
                    # Calculamos la tasa específica de este centro
                    tasa_centro = calcular_tasa_exito(curso, campana, centro, materia)

                    diferencia = None
                    if tasa_centro is not None and tasa_global is not None:
                        diferencia = tasa_centro - tasa_global

                    filas_centros.append({
                        'centro': centro,
                        'tasa': tasa_centro,
                        'diferencia': diferencia  # Pasamos el dato ya calculado
                    })

                datos_informe.append({
                    'materia': materia,
                    'tasa_global': tasa_global,
                    'filas': filas_centros
                })

            context = self.get_context_data(**kwargs)
            context.update({
                'campana': campana,
                'datos': datos_informe,
            })

            self.pdf_filename = f"Rendimiento_Dptos_{campana.descripcion}.pdf"
            return self.render_to_response(context)

        # Si es solo cambio de selectores, repintamos form
        return render(request, 'form_rendimiento_dptos.html', {'form': form})


class IntroducirInformeHistoricoView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'form_introducir_historico.html'

    def test_func(self):
        return self.request.user.groups.filter(name='jefatura de estudios').exists()

    def get(self, request):
        form = InformeHistoricoForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        # Instanciamos el form con los datos del POST
        form = InformeHistoricoForm(request.POST)

        # Detectamos si es una acción de guardar o solo cambio de desplegable
        es_guardado = 'guardar_datos' in request.POST

        # Recuperamos los objetos seleccionados para buscar el informe
        campana_id = request.POST.get('campana_seleccion')
        centro_id = request.POST.get('centro_seleccion')
        materia_id = request.POST.get('materia_seleccion')

        informe_existente = None

        if campana_id and centro_id and materia_id:
            informe_existente = InformeDepartamento.objects.filter(
                campana_id=campana_id,
                centro_origen_id=centro_id,
                materia_id=materia_id
            ).first()

        # CASO 1: El usuario quiere GUARDAR
        if es_guardado:
            if form.is_valid():
                if not (campana_id and centro_id and materia_id):
                    messages.error(request, "Debes seleccionar todos los campos (Campaña, Centro y Materia).")
                else:
                    # Si ya existía, actualizamos ese. Si no, creamos uno nuevo.
                    if informe_existente:
                        informe = informe_existente
                    else:
                        informe = InformeDepartamento(
                            campana_id=campana_id,
                            centro_origen_id=centro_id,
                            materia_id=materia_id
                        )

                    # Guardamos los campos de texto
                    informe.cuestiones_generales = form.cleaned_data['cuestiones_generales']
                    informe.fortalezas = form.cleaned_data['fortalezas']
                    informe.debilidades = form.cleaned_data['debilidades']
                    informe.save()

                    messages.success(request, f"Informe guardado correctamente para {informe.materia}.")
                    # Opcional: limpiar el formulario o mantenerlo
                    return redirect('transito:introducir_historico')
            else:
                messages.error(request, "Por favor, corrige los errores en el formulario.")

        # CASO 2: El usuario solo cambió un DESPLEGABLE (Recarga AJAX/Submit)
        else:
            # Si hemos encontrado un informe en la BD, cargamos sus datos en el formulario
            # para que el usuario los vea y pueda editarlos.
            if informe_existente:
                # Re-instanciamos el formulario pero inyectando los valores iniciales del objeto encontrado
                # manteniendo la selección de los desplegables (request.POST)
                initial_data = {
                    'cuestiones_generales': informe_existente.cuestiones_generales,
                    'fortalezas': informe_existente.fortalezas,
                    'debilidades': informe_existente.debilidades
                }
                # Fusionamos POST y initial es un poco truco en Django,
                # así que mejor creamos un form nuevo mezclando datos
                form = InformeHistoricoForm(initial=initial_data)
                # Forzamos que los selects tengan el valor seleccionado en el POST
                form.fields['curso'].initial = request.POST.get('curso')
                form.fields['campana_seleccion'].initial = campana_id
                form.fields['centro_seleccion'].initial = centro_id
                form.fields['materia_seleccion'].initial = materia_id

                # Importante: volver a filtrar los querysets porque al hacer new Form() se resetean
                # (Aunque la lógica del __init__ debería leer del 'data' o 'initial' si se pasa correctamente,
                #  para simplificar, pasamos el request.POST como data pero usamos initial para los textos)

                # ESTRATEGIA MÁS LIMPIA:
                # Usamos el form original (bound) pero modificamos sus valores 'value' manualmente
                # para los campos de texto si no es guardado.
                form = InformeHistoricoForm(request.POST)  # Bound form
                # Sobreescribimos los campos de texto con lo que hay en BD
                form.data = form.data.copy()  # Hacemos mutable el QueryDict
                form.data['cuestiones_generales'] = informe_existente.cuestiones_generales
                form.data['fortalezas'] = informe_existente.fortalezas
                form.data['debilidades'] = informe_existente.debilidades
                # Es necesario volver a instanciar para que coja los nuevos datos
                form = InformeHistoricoForm(form.data)

        return render(request, self.template_name, {
            'form': form,
            'informe_encontrado': (informe_existente is not None)
        })