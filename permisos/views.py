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
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.dateparse import parse_datetime

from centro.views import group_check_je
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from centro.utils import get_current_academic_year

from .models import AsuntoPropio
from centro.models import Profesores, CursoAcademico
from django.utils import timezone


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def crear_asunto_propio(request):
    """Vista para jefatura: registrar solicitudes de asuntos propios"""
    curso_actual = get_current_academic_year()

    if request.method == 'POST':
        profesor_id = request.POST.get('profesor')
        fecha_str = request.POST.get('fecha')

        if not profesor_id or not fecha_str:
            messages.error(request, "Debes seleccionar profesor y fecha.", extra_tags='danger')
            return redirect('permisos:crear_asunto_propio')

        try:
            profesor = get_object_or_404(Profesores, pk=profesor_id, Baja=False)
            if '/' in fecha_str:
                fecha = timezone.datetime.strptime(fecha_str, '%d/%m/%Y').date()
            else:
                fecha = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Fecha inválida.", extra_tags='danger')
            return redirect('permisos:crear_asunto_propio')

        # 1) Límite de 4 personas ese día (pendientes + aprobadas)
        total_dia = AsuntoPropio.objects.filter(
            curso_academico=curso_actual,
            fecha=fecha,
            estado__in=['P', 'A']  # Pendientes y Aprobadas cuentan
        ).count()

        if total_dia >= 4:
            messages.error(
                request,
                f"Ya hay {total_dia} solicitudes/aprobaciones para el {fecha_str}. "
                "Máximo permitido: 4.", extra_tags='danger'
            )
            return redirect('permisos:crear_asunto_propio')

        # 2) Límite de 2 solicitudes por profesor en todo el curso (P + A)
        total_profesor_curso = AsuntoPropio.objects.filter(
            curso_academico=curso_actual,
            profesor=profesor,
            estado__in=['P', 'A']
        ).count()

        if total_profesor_curso >= 2:
            messages.error(
                request,
                f"{profesor} ya tiene {total_profesor_curso} solicitudes en el curso actual. "
                "Máximo permitido: 2.", extra_tags='danger'
            )
            return redirect('permisos:crear_asunto_propio')

        # Si pasa las validaciones, crear o actualizar el registro
        asunto, created = AsuntoPropio.objects.get_or_create(
            profesor=profesor,
            fecha=fecha,
            curso_academico=curso_actual,
        )

        accion = "creada" if created else "actualizada"
        messages.success(
            request,
            f"Solicitud {accion}: {profesor} - {fecha_str}"
        )

        return redirect('permisos:crear_asunto_propio')

    contexto = {
        'profesores': Profesores.objects.filter(Baja=False).order_by('Apellidos', 'Nombre'),
        'curso_actual': curso_actual,
    }
    return render(request, 'crear_asunto_propio.html', contexto)
@login_required(login_url='/')
def calendario_asuntos_propios(request):
    """Calendario público para profesores (solo lectura)"""
    return render(request, 'calendario_asuntos_propios.html')


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def lista_asuntos_propios(request):
    curso_actual = get_current_academic_year()

    solicitudes = (AsuntoPropio.objects
                   .filter(curso_academico=curso_actual)
                   .select_related('profesor', 'curso_academico')
                   .order_by('-fecha', 'profesor__Apellidos'))

    # Filtros
    estado = request.GET.get('estado', '')
    if estado:
        solicitudes = solicitudes.filter(estado=estado)

    # 👇 CALCULAR ESTADÍSTICAS EN LA VISTA
    total_pendientes = solicitudes.filter(estado='P').count()
    total_aprobadas = solicitudes.filter(estado='A').count()
    total_rechazadas = solicitudes.filter(estado='R').count()
    total_solicitudes = solicitudes.count()

    profesores = Profesores.objects.filter(Baja=False).order_by('Apellidos', 'Nombre')

    contexto = {
        'solicitudes': solicitudes,
        'total_solicitudes': total_solicitudes,
        'total_pendientes': total_pendientes,
        'total_aprobadas': total_aprobadas,
        'total_rechazadas': total_rechazadas,
        'curso_actual': curso_actual,
        'profesores': profesores
    }
    return render(request, 'lista_asuntos_propios.html', contexto)


@login_required(login_url='/')
def api_asuntos_propios_calendar(request):
    """API JSON para FullCalendar - solo conteos por día"""
    curso_actual = get_current_academic_year()
    inicio_iso = request.GET.get('start')
    fin_iso = request.GET.get('end')

    if not inicio_iso or not fin_iso:
        return JsonResponse([])

    # Convertir ISO con timezone a date pura
    try:
        inicio_dt = parse_datetime(inicio_iso)
        fin_dt = parse_datetime(fin_iso)
        if inicio_dt:
            inicio = inicio_dt.date()
        if fin_dt:
            fin = fin_dt.date()
    except:
        return JsonResponse([])

    qs = (AsuntoPropio.objects
          .filter(curso_academico=curso_actual,
                  fecha__gte=inicio,
                  fecha__lte=fin)
          .values('fecha')
          .annotate(
              total=Count('id'),
              aprobados=Count('id', filter=Q(estado='A')),
              pendientes=Count('id', filter=Q(estado='P')),
              rechazados=Count('id', filter=Q(estado='R')),
          ))

    events = []
    for row in qs:
        fecha = row['fecha']
        total = row['total']
        aprobados = row['aprobados']
        pendientes = row['pendientes']

        # Título del evento
        partes = []
        if aprobados:
            partes.append(f"{aprobados} aprobadas")
        if pendientes:
            partes.append(f"{pendientes} pendientes")

        titulo = f"{total} solicitud/es" if total > 0 else "Sin solicitudes"

        # Color según saturación
        color = '#28a745'  # Verde
        if total >= 3:
            color = '#FFA500'  # Naranja
        if total >= 4:
            color = '#dc3545'  # Rojo

        events.append({
            "title": titulo,
            "start": fecha.isoformat(),  # ← YYYY-MM-DD limpio
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color,
        })

    return JsonResponse(events, safe=False)


@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def eliminar_asunto_propio(request):
    """Vista AJAX para eliminar solicitud"""
    if request.method == 'POST':
        id_solicitud = request.POST.get('id')

        try:
            solicitud = get_object_or_404(AsuntoPropio, id=id_solicitud)
            solicitud.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})

