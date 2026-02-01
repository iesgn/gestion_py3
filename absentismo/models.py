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


from django.db import models

from centro.models import Alumnos, Profesores, CursoAcademico


# Create your models here.
class TiposActuaciones(models.Model):
    TipoActuacion = models.CharField(max_length=60)


    def __str__(self):
        return self.TipoActuacion

    class Meta:
        verbose_name = "Tipo Actuación"
        verbose_name_plural = "Tipos de Actuación"

class ProtocoloAbs(models.Model):
    alumno = models.ForeignKey(Alumnos, related_name='protocolos', on_delete=models.CASCADE)
    tutor = models.ForeignKey(Profesores, related_name='tutor', on_delete=models.CASCADE)
    fecha_apertura = models.DateField()
    fecha_cierre = models.DateField(blank=True, null=True)
    abierto = models.BooleanField(default=False)

    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.SET_NULL, null=True, blank=True)


    def __str__(self):
        return f"Protocolo absentismo para {self.alumno.Nombre}, abierto por {self.tutor}"

    class Meta:
        verbose_name="Protocolo Absentismo"
        verbose_name_plural="Protocolos Absentismo"


class Actuaciones(models.Model):
    medios = (
        ('1', 'Teléfono'),
        ('2', 'PASEN'),
        ('3', 'Correo ordinario'),
        ('4', 'Correo certificado'),
        ('5', 'Otros'),
    )
    Protocolo = models.ForeignKey(ProtocoloAbs,  related_name='actuaciones', on_delete=models.CASCADE)
    Fecha = models.DateField()
    Tipo = models.ForeignKey(TiposActuaciones, related_name='Tipo_de', blank=True, null=True, on_delete=models.SET_NULL)
    Comentario = models.TextField(blank=True)
    Notificada = models.BooleanField(default=False)
    Medio = models.CharField(max_length=1, choices=medios,blank=True, null=True)
    Telefono = models.TextField(blank=True, null=True)
    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.SET_NULL, null=True, blank=True)


    def __unicode__(self):
        return self.Protocolo

    class Meta:
        verbose_name = "Actuación"
        verbose_name_plural = "Actuaciones"

class FaltasProtocolo(models.Model):
    Protocolo = models.ForeignKey(ProtocoloAbs, related_name='faltas', on_delete=models.CASCADE)
    Fecha = models.DateField()
    DiaCompletoJustificada = models.PositiveSmallIntegerField(blank=True, null=True)
    DiaCompletoNoJustificada = models.PositiveSmallIntegerField(blank=True, null=True)
    TramosJustificados = models.PositiveSmallIntegerField(blank=True, null=True)
    TramosNoJustificados = models.PositiveSmallIntegerField(blank=True, null=True)
    NotificacionDiaCompleto = models.PositiveSmallIntegerField(blank=True, null=True)
    NotificacionTramos = models.PositiveSmallIntegerField(blank=True, null=True)

    def __str__(self):
        return f'Faltas del protocolo {self.Protocolo} en {self.Fecha}'

    class Meta:
        verbose_name = "Faltas de un protocolo"
        verbose_name_plural = "Faltas de los protocolos"