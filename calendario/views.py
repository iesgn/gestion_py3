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


from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import date, timedelta
from convivencia.models import Amonestaciones, Sanciones
from centro.models import Alumnos
from centro.views import group_check_je
from absentismo.models import FaltasProtocolo, ProtocoloAbs


# ToDo: Añadir texto a loes eventos de calendario.

# Create your views here.
@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def faltas(request, proto_id):
    protocolo = ProtocoloAbs.objects.get(id=proto_id)
    alumno = protocolo.alumno
    context = {
        'tipo': 'faltas',
        'alumno': alumno,
        'protocolo': protocolo,
    }
    return render(request, 'calendario.html', context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def faltas_json(request, proto_id):
    faltas = FaltasProtocolo.objects.filter(Protocolo__id=proto_id).all()

    eventos = []
    faltasNJ_tramos = []

    for falta in faltas:
        if (falta.DiaCompletoNoJustificada > 0) or (falta.TramosNoJustificados > 4):
            if falta.DiaCompletoNoJustificada > 0:
                tramos = 6
            if falta.TramosNoJustificados > 4:
                tramos = falta.TramosNoJustificados
                falta_data = {
                    'start': falta.Fecha.strftime("%Y-%m-%d"),
                    'className': 'bg-secondary',
                    'modalInfo': [
                        {'label': 'Tipo de falta', 'text': 'A día completo no justificada.'},
                        {'label': 'Número de tramos', 'text': f'{tramos}'}
                    ]
                }
                eventos.append(falta_data)
        if (falta.DiaCompletoNoJustificada == 0) and (falta.TramosNoJustificados > 0) and (falta.TramosNoJustificados <= 4):
            falta_data = {
                'start': falta.Fecha.strftime("%Y-%m-%d"),
                'className': 'bg-warning',
                'modalInfo': [
                    {'label': 'Tipo de falta', 'text': 'A tramos no justificada.'},
                    {'label': 'Número de tramos', 'text': f'{falta.TramosNoJustificados}'}
                ]
            }
            eventos.append(falta_data)
        if (falta.DiaCompletoJustificada > 0):
            falta_data = {
                'start': falta.Fecha.strftime("%Y-%m-%d"),
                'className': 'bg-success',
                'modalInfo': [
                    {'label': 'Tipo de falta', 'text': 'Día completo justificada.'},
                ]
            }
            eventos.append(falta_data)
        if falta.TramosJustificados > 0:
            falta_data = {
                'start': falta.Fecha.strftime("%Y-%m-%d"),
                'className': 'bg-success',
                'modalInfo': [
                    {'label': 'Tipo de falta', 'text': 'A tramos justificada.'},
                    {'label': 'Número de tramos', 'text': f'{falta.TramosJustificados}'}
                ]
            }
            eventos.append(falta_data)
    return JsonResponse(eventos, safe=False)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def amonestaciones(request, alum_id):
    alumno = Alumnos.objects.get(id=alum_id)
    context = {
        'alumno': alumno,
        'tipo': 'amonestaciones'
    }
    return render(request, "amonestaciones.html", context)

@login_required(login_url='/')
@user_passes_test(group_check_je, login_url='/')
def amonestaciones_json(request, alum_id):
    amonestaciones = Amonestaciones.objects.filter(IdAlumno_id=alum_id)
    sanciones = Sanciones.objects.filter(IdAlumno_id=alum_id)

    leves = []
    graves = []
    lsanciones = []

    for amonestacion in amonestaciones:
        amonestacion_data = {
            'start': amonestacion.Fecha.strftime("%Y-%m-%d"),
            'className': 'bg-warning' if amonestacion.Tipo.TipoFalta in ("L", None) else 'bg-secondary',
            'modalInfo': [
                {'label': 'Tipo de amonestación.', 'text': amonestacion.Tipo.TipoAmonestacion},
                {'label': 'Descripción:', 'text':amonestacion.Comentario}
            ]
        }
        if amonestacion.Tipo.TipoFalta == "L":
            leves.append(amonestacion_data)
        elif amonestacion.Tipo.TipoFalta == "G":
            graves.append(amonestacion_data)

    for sancion in sanciones:
        inicio = sancion.Fecha.strftime("%Y-%m-%d")
        final = (sancion.Fecha_fin + timedelta(days=1)).strftime("%Y-%m-%d")
        lsanciones.append({
            'start': inicio,
            'end': final,
            'className': 'bg-danger',
            'modalInfo': [
                {'label': 'Sanción:', 'text': sancion.Sancion},
                {'label': 'Comentario:', 'text': sancion.Comentario}
            ]
        })

    return JsonResponse({
        'leves': leves,
        'graves': graves,
        'sanciones': lsanciones
    }, safe=False)