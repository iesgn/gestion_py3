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
from centro.models import Cursos, Alumnos, Profesores, CursoAcademico

class EstadoActividad(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Estado de actividad"
        verbose_name_plural = "Estados de actividad"
        ordering = ['nombre']


class Actividades(models.Model):

    Titulo = models.CharField(max_length=255)
    Descripcion = models.TextField(blank=True, null=True)
    Responsable = models.ForeignKey(Profesores, on_delete=models.CASCADE, related_name='actividades_organizadas')
    FechaInicio = models.DateField()
    FechaFin = models.DateField()
    HoraSalida = models.TimeField(blank=True, null=True)
    HoraLlegada = models.TimeField(blank=True, null=True)
    UnidadesAfectadas = models.ManyToManyField(Cursos)
    Alumnado = models.ManyToManyField(Alumnos, through='ActividadAlumno', related_name="actividades_participadas")
    Profesorado = models.ManyToManyField(Profesores, related_name="actividades_participadas")
    CosteAlumnado = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    AportacionCentro = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    Estado = models.ForeignKey(EstadoActividad, on_delete=models.PROTECT, related_name='actividades')
    EnProgramacion = models.BooleanField(default=False)

    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.Titulo

    class Meta:
        verbose_name="Actividad DACE"
        verbose_name_plural="Actividades DACE"
        unique_together = ('Titulo', 'Descripcion', 'Responsable', 'FechaInicio', 'FechaFin', 'HoraSalida', 'HoraLlegada')


class ActividadAlumno(models.Model):
    actividad = models.ForeignKey(Actividades, on_delete=models.CASCADE, related_name="actividad_alumno")
    alumno = models.ForeignKey(Alumnos, on_delete=models.CASCADE, related_name="actividades")
    ha_pagado = models.BooleanField(default=False)
    compe = models.BooleanField(default=False)

    class Meta:
        unique_together = ('actividad', 'alumno')

class Aprobaciones(models.Model):
    APROBACION_CHOICES = [
        ('Consejo Escolar', 'Consejo Escolar'),
        ('Comisión Permanente', 'Comision Permanente'),
    ]
    Actividad = models.ForeignKey(Actividades, on_delete=models.CASCADE, related_name='aprobaciones')
    AprobadoPor = models.CharField(max_length=50, choices=APROBACION_CHOICES)
    Fecha = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Aprobación de {self.actividad.titulo}"


class GastosActividad(models.Model):
    TIPO_CHOICES = [
        ('General', 'General'),
        ('Por alumno', 'Por alumno'),
    ]

    actividad = models.ForeignKey(Actividades, on_delete=models.CASCADE, related_name="gastos")
    concepto = models.CharField(max_length=255)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='General')

    def __str__(self):
        return f"{self.concepto} ({self.tipo}) - {self.importe}€"


