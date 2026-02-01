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

from collections import OrderedDict, defaultdict
from sqlite3 import IntegrityError

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

# Create your views here.
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, DeleteView, CreateView

from centro.models import Cursos, Aulas
from centro.utils import get_current_academic_year
from centro.views import group_check_prof, group_check_prof_or_guardia, group_check_je, \
    group_check_prof_or_guardia_or_conserje
from .forms import ItemHorarioForm, CopiarHorarioForm
from .models import Profesores, ItemHorario

@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia_or_conserje, login_url='/')
def horario_profesor_view(request):

    curso_academico_actual = get_current_academic_year()
    profesor_id = request.GET.get('profesor')  # Obtener el ID del profesor seleccionado desde el GET
    profesores = Profesores.objects.filter(Baja=False)  # Lista de todos los profesores para el desplegable

    items_horario = None
    if profesor_id:
        profesor = Profesores.objects.get(id=profesor_id)


        # Filtrar los horarios por el profesor seleccionado y ordenar por día y tramo
        items_horario = ItemHorario.objects.filter(profesor_id=profesor_id, curso_academico=curso_academico_actual).order_by('dia', 'tramo')

    # Crear un diccionario para el horario
    horario = {tramo: {dia: [] for dia in range(1, 6)} for tramo in range(1, 8)}
    tramos = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']

    # Diccionario para almacenar las unidades y sus materias
    unidades_dict = {}

    if items_horario:
        # Rellenar el diccionario con los ítems del horario
        for item in items_horario:
            # Si ya existen items para este tramo y día, añadimos las unidades
            for existing_item in horario[item.tramo][item.dia]:
                if (existing_item.profesor == item.profesor and
                        existing_item.materia == item.materia and
                        existing_item.aula == item.aula):
                    # Añadimos la nueva unidad al campo virtual 'unidades_combinadas'
                    existing_item.unidades_combinadas += f", {item.unidad}"
                    break
            else:
                # Si no hay coincidencias, añadimos el ítem nuevo con la unidad inicial
                item.unidades_combinadas = str(item.unidad)  # Inicializar el campo virtual
                horario[item.tramo][item.dia].append(item)

            # Llenar el diccionario de unidades y materias
            if "GUARDIA" not in str(item.unidad).upper() and "GUARDIA" not in str(item.materia).upper():
                unidad_id = item.unidad.id
                unidad_nombre = item.unidad.Curso
                materia_nombre = item.materia

                # Si la unidad ya está en el diccionario, añadimos la materia si no está
                if unidad_id in unidades_dict:
                    if materia_nombre not in unidades_dict[unidad_id]['materias']:
                        unidades_dict[unidad_id]['materias'].append(materia_nombre)
                else:
                    # Crear una nueva entrada para la unidad con su nombre y una lista de materias
                    unidades_dict[unidad_id] = {'nombre': unidad_nombre, 'materias': [materia_nombre]}

    # Ordenar las unidades por su ID
    unidades_dict = OrderedDict(sorted(unidades_dict.items()))

    # Formatear el listado de unidades y materias para el contexto
    unidades_materias = [
        {'unidad': unidad_data['nombre'], 'materias': ', '.join(unidad_data['materias'])}
        for unidad_id, unidad_data in unidades_dict.items()
    ]

    context = {
        'profesores': profesores,
        'horario': horario,
        'tramos': tramos,  # Pasar el rango de tramos al contexto
        'dias': range(1, 6),  # Pasar el rango de días al contexto
        'menu_horarios': True,
        'unidades_materias': unidades_materias
    }
    return render(request, 'horario_profesor.html', context)


@login_required(login_url='/')
@user_passes_test(group_check_prof, login_url='/')
def mihorario(request):

    if not hasattr(request.user, 'profesor'):
        return render(request, 'error.html', {'message': 'No tiene un perfil de profesor asociado.'})

    profesor = request.user.profesor
    curso_academico_actual = get_current_academic_year()

    items_horario = None
    if profesor:

        # Filtrar los horarios por el profesor seleccionado y ordenar por día y tramo
        items_horario = ItemHorario.objects.filter(profesor=profesor, curso_academico=curso_academico_actual).order_by('dia', 'tramo')

    # Crear un diccionario para el horario
    horario = {tramo: {dia: [] for dia in range(1, 6)} for tramo in range(1, 8)}
    tramos = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']

    if items_horario:
        # Rellenar el diccionario con los ítems del horario
        for item in items_horario:
            # Si ya existen items para este tramo y día, añadimos las unidades
            for existing_item in horario[item.tramo][item.dia]:
                if (existing_item.profesor == item.profesor and
                        existing_item.materia == item.materia and
                        existing_item.aula == item.aula):
                    # Añadimos la nueva unidad al campo virtual 'unidades_combinadas'
                    existing_item.unidades_combinadas += f", {item.unidad}"
                    break
            else:
                # Si no hay coincidencias, añadimos el ítem nuevo con la unidad inicial
                item.unidades_combinadas = str(item.unidad)  # Inicializar el campo virtual
                horario[item.tramo][item.dia].append(item)

    context = {
        'profesor': profesor,
        'horario': horario,
        'tramos': tramos,  # Pasar el rango de tramos al contexto
        'dias': range(1, 6),  # Pasar el rango de días al contexto
        'menu_horarios': True
    }
    return render(request, 'mihorario.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia_or_conserje, login_url='/')
def horario_curso_view(request):
    curso_id = request.GET.get('curso')  # Obtener el ID del curso seleccionado desde el GET
    cursos = Cursos.objects.all()  # Lista de todos los cursos para el desplegable

    items_horario = None
    profesores_materias = defaultdict(list)
    tutor = None
    curso_academico_actual = get_current_academic_year()

    if curso_id:
        # Filtrar los horarios por el curso seleccionado y ordenar por día y tramo
        items_horario = ItemHorario.objects.filter(
            Q(unidad_id=curso_id) & Q(profesor__Baja=False) & Q(curso_academico=curso_academico_actual)
        ).order_by('dia', 'tramo')

        # Obtener el curso y su tutor
        curso = Cursos.objects.filter(id=curso_id).first()
        if curso and curso.Tutor:
            tutor = curso.Tutor  # Asignar el tutor del curso

        # Agrupar profesores y materias en el curso
        for item in items_horario:
            if item.profesor and item.materia:  # Asegurarse de que hay un profesor y una materia en el ItemHorario
                profesores_materias[item.profesor].append(item.materia)

    # Crear un diccionario para el horario
    horario = {tramo: {dia: [] for dia in range(1, 6)} for tramo in range(1, 8)}
    tramos = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']

    if items_horario:
        # Rellenar el diccionario con los ítems del horario
        for item in items_horario:
            horario[item.tramo][item.dia].append(item)

    # Convertir materias en una lista única por profesor
    profesores_materias = {profesor: ', '.join(set(materias)) for profesor, materias in profesores_materias.items()}

    context = {
        'cursos': cursos,
        'horario': horario,
        'tramos': tramos,  # Pasar el rango de tramos al contexto
        'dias': range(1, 6),  # Pasar el rango de días al contexto
        'profesores_materias': profesores_materias,
        'tutor': tutor,
        'menu_horarios': True
    }
    return render(request, 'horario_grupo.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_prof_or_guardia_or_conserje, login_url='/')
def horario_aula_view(request):
    aula_id = request.GET.get('aula')  # Obtener el ID del curso seleccionado desde el GET
    aulas = Aulas.objects.all()  # Lista de todos los cursos para el desplegable

    items_horario = None
    profesores_materias = defaultdict(list)
    curso_academico_actual = get_current_academic_year()

    if aula_id:
        # Filtrar los horarios por el curso seleccionado y ordenar por día y tramo
        items_horario = ItemHorario.objects.filter(
            Q(aula_id=aula_id) & Q(profesor__Baja=False) & Q(curso_academico=curso_academico_actual)
        ).order_by('dia', 'tramo')

        # Obtener el curso y su tutor
        # curso = Cursos.objects.filter(id=curso_id).first()
        # if curso and curso.Tutor:
        #     tutor = curso.Tutor  # Asignar el tutor del curso

        # Agrupar profesores y materias en el curso
        for item in items_horario:
            if item.profesor and item.materia:  # Asegurarse de que hay un profesor y una materia en el ItemHorario
                profesores_materias[item.profesor].append(item.materia)

    # Crear un diccionario para el horario
    horario = {tramo: {dia: [] for dia in range(1, 6)} for tramo in range(1, 8)}
    tramos = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']

    if items_horario:
        # Rellenar el diccionario con los ítems del horario
        for item in items_horario:
            horario[item.tramo][item.dia].append(item)

    context = {
        'aulas': aulas,
        'horario': horario,
        'tramos': tramos,  # Pasar el rango de tramos al contexto
        'dias': range(1, 6),  # Pasar el rango de días al contexto
        'menu_horarios': True
    }
    return render(request, 'horario_aula.html', context)

class EditarHorarioProfesorView(ListView):
    model = ItemHorario
    template_name = 'editar_horario_profesor.html'
    context_object_name = 'items_horario'
    curso_academico_actual = get_current_academic_year()

    def get_queryset(self):
        profesor_id = self.kwargs['profesor_id']
        curso_academico_actual = get_current_academic_year()
        return ItemHorario.objects.filter(profesor__id=profesor_id, curso_academico=curso_academico_actual).order_by('dia', 'tramo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profesor'] = get_object_or_404(Profesores, id=self.kwargs['profesor_id'])
        context['form'] = ItemHorarioForm()  # Pasar el formulario al contexto
        return context


class UpdateHorarioView(UpdateView):
    model = ItemHorario
    form_class = ItemHorarioForm
    template_name = 'editar_item_horario.html'

    def get_success_url(self):
        # Obtener el ID del profesor desde el objeto ItemHorario actualizado
        profesor_id = self.object.profesor.id
        # Redirigir a la vista 'editar_horario_profesor' pasando el profesor_id
        return reverse_lazy('editar_horario_profesor', kwargs={'profesor_id': profesor_id})

    def form_valid(self, form):
        # Captura los valores antiguos antes de guardar (antes de super().form_valid)
        item_antiguo = ItemHorario.objects.get(pk=self.object.pk)
        datos_clave = {
            'tramo': item_antiguo.tramo,
            'dia': item_antiguo.dia,
            'unidad': item_antiguo.unidad,
            'aula': item_antiguo.aula,
            'materia': item_antiguo.materia,
            'curso_academico': item_antiguo.curso_academico,
        }

        response = super().form_valid(form)
        item = self.object
        profesor = item.profesor

        if profesor.SustitutoDe:
            otro_profesor = profesor.SustitutoDe
        else:
            try:
                otro_profesor = Profesores.objects.get(SustitutoDe=profesor)
            except Profesores.DoesNotExist:
                otro_profesor = None

        if otro_profesor:
            # Buscar el item horario equivalente con los datos clave previos
            try:
                item_otro = ItemHorario.objects.get(profesor=otro_profesor, **datos_clave)
                # Ahora actualiza todos los campos que quieres sincronizar
                item_otro.tramo = item.tramo
                item_otro.dia = item.dia
                item_otro.unidad = item.unidad
                item_otro.aula = item.aula
                item_otro.materia = item.materia
                item_otro.curso_academico = item.curso_academico
                item_otro.save()
            except ItemHorario.DoesNotExist:
                # Si no existía, créalo (caso poco frecuente)
                ItemHorario.objects.create(
                    tramo=item.tramo,
                    dia=item.dia,
                    profesor=otro_profesor,
                    unidad=item.unidad,
                    aula=item.aula,
                    materia=item.materia,
                    curso_academico=item.curso_academico
                )

        return response


class DeleteHorarioView(DeleteView):
    model = ItemHorario
    template_name = 'confirmar_eliminar_horario.html'

    def get_success_url(self):
        return reverse_lazy('editar_horario_profesor', kwargs={'profesor_id': self.object.profesor.id})

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        profesor = obj.profesor

        datos_clave = {
            'tramo': obj.tramo,
            'dia': obj.dia,
            'unidad': obj.unidad,
            'aula': obj.aula,
            'materia': obj.materia,
            'curso_academico': obj.curso_academico,
        }

        if profesor.SustitutoDe:
            otro_profesor = profesor.SustitutoDe
        else:
            try:
                otro_profesor = Profesores.objects.get(SustitutoDe=profesor)
            except Profesores.DoesNotExist:
                otro_profesor = None

        if otro_profesor:
            ItemHorario.objects.filter(profesor=otro_profesor, **datos_clave).delete()

        return super().delete(request, *args, **kwargs)


class CrearItemHorarioView(CreateView):
    model = ItemHorario
    form_class = ItemHorarioForm
    template_name = 'editar_horario_profesor.html'

    def form_valid(self, form):
        item = form.save(commit=False)
        item.profesor = get_object_or_404(Profesores, id=self.kwargs['profesor_id'])
        try:
            item.save()
        except IntegrityError:
            print("Ya existe un ItemHorario igual")
            return super().form_invalid(form)

        # Sincronizar con sustituto o titular
        profesor = item.profesor
        if profesor.SustitutoDe:
            otro_profesor = profesor.SustitutoDe
        else:
            try:
                otro_profesor = Profesores.objects.get(SustitutoDe=profesor)
            except Profesores.DoesNotExist:
                otro_profesor = None

        if otro_profesor:
            ItemHorario.objects.update_or_create(
                tramo=item.tramo,
                dia=item.dia,
                profesor=otro_profesor,
                unidad=item.unidad,
                aula=item.aula,
                materia=item.materia,
                curso_academico=item.curso_academico,
                defaults={
                    'materia': item.materia
                }
            )

        # Respuesta AJAX
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            data = {
                'id': item.id,
                'tramo': item.get_tramo_display(),
                'dia': item.get_dia_display(),
                'materia': item.materia,
                'aula': item.aula.Aula
            }
            return JsonResponse(data)

        return super().form_valid(form)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def aulas_libres(request):
    # Obtener todas las aulas que no contengan las palabras clave

    curso_academico_actual = get_current_academic_year()

    aulas = Aulas.objects.exclude(
        Aula__icontains='Maleta'
    ).exclude(
        Aula__icontains='Carro'
    ).exclude(
        Aula__icontains='Moodle'
    ).exclude(
        Aula__icontains='Otros'
    ).exclude(
        Aula__icontains='profesores'
    ).exclude(
        Aula__icontains='Dpto'
    ).exclude(
        Aula__icontains='Biblioteca'
    ).exclude(
        Aula__icontains='familias'
    ).exclude(
        Aula__icontains='Laboratorio'
    ).exclude(
        Aula__icontains='Convivencia'
    ).exclude(
        Aula__icontains='Música'
    ).exclude(
        Aula__icontains='Taller'
    ).exclude(
        Aula__icontains='Dpcho.'
    ).exclude(
        Aula__icontains='Horizonte'
    )

    tramos = ['1ª hora', '2ª hora', '3ª hora', 'RECREO', '4ª hora', '5ª hora', '6ª hora']

    # Obtener todos los ítems de horario
    items_horario = ItemHorario.objects.filter(curso_academico=curso_academico_actual)

    # Crear un diccionario para las aulas libres
    horario_aulas_libres = {tramo: {dia: [] for dia in range(1, 6)} for tramo in range(1, 8)}

    # Llenar el diccionario de aulas libres
    for aula in aulas:
        for tramo in range(1, 8):
            if tramo == 4:
                continue
            for dia in range(1, 6):
                # Comprobar si la aula está ocupada en el tramo y día específicos
                if not items_horario.filter(aula=aula, tramo=tramo, dia=dia).exists():
                    horario_aulas_libres[tramo][dia].append(aula)

    context = {
        'aulas_libres': horario_aulas_libres,
        'tramos': tramos,
        'dias': range(1, 6),
        'menu_horarios': True
    }


    return render(request, 'aulas_libres.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def copiar_horario(request):

    if request.method == 'POST':
        form = CopiarHorarioForm(request.POST)
        if form.is_valid():

            curso_academico_actual = get_current_academic_year()
            profe_origen = form.cleaned_data['ProfesorOrigen']
            profe_destino = form.cleaned_data['ProfesorDestino']

            # Copiar horario
            try:
                horario_origen = ItemHorario.objects.filter(profesor=profe_origen, curso_academico=curso_academico_actual)

                # Borrar horario del profesor de destino antes de copiar
                ItemHorario.objects.filter(profesor=profe_destino, curso_academico=curso_academico_actual).delete()

                items_nuevos = []
                for item in horario_origen:
                    nuevo_item = ItemHorario(
                        tramo=item.tramo,
                        dia=item.dia,
                        profesor=profe_destino,
                        unidad=item.unidad,
                        aula=item.aula,
                        materia=item.materia,
                        curso_academico=curso_academico_actual
                    )
                    items_nuevos.append(nuevo_item)

                ItemHorario.objects.bulk_create(items_nuevos)

                print(f"Horario de {profe_origen} copiado exitosamente a {profe_destino}.")
                context = {'form': form, 'profe_origen': profe_origen, 'profe_destino': profe_destino, 'exito': True}
            except ObjectDoesNotExist as e:
                print(f"Error: {e}")
                context = {'form': form, 'exito': False, 'error': e}

        else:
            context = {'form': form, 'exito': False, 'error': form.errors}
    else:
        form = CopiarHorarioForm()
        context = {'form': form}

    return render(request, 'copiar_horario.html', context)

