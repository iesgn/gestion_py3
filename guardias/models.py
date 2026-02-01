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

from centro.models import Profesores, Cursos, Aulas, CursoAcademico


# Create your models here.
class ItemGuardia(models.Model):
    TRAMOS = [(i, f'Tramo {i}') for i in range(1, 8)]
    TRAMO_CHOICES = [
        (1, '1ª Hora'),
        (2, '2ª Hora'),
        (3, '3ª Hora'),
        (4, 'RECREO'),
        (5, '4ª Hora'),
        (6, '5ª Hora'),
        (7, '6ª Hora'),
    ]

    Unidad = models.ForeignKey(Cursos, blank=True, null=True, on_delete=models.SET_NULL)
    ProfesorAusente = models.ForeignKey(Profesores, blank=True, null=True, on_delete=models.SET_NULL, related_name='guardias_ausente')
    ProfesoresGuardia = models.ManyToManyField(Profesores, verbose_name="Profesorado Guardia", blank=True, related_name='guardias_profesoradoguardia')
    Aula = models.ForeignKey(Aulas, related_name='guardias_aula', blank=True, null=True, on_delete=models.SET_NULL)
    Tarea = models.CharField(max_length=255, blank=True, null=True)
    Materia = models.CharField(max_length=255, blank=True, null=True)
    Fecha = models.DateField()
    Tramo = models.IntegerField(choices=TRAMO_CHOICES)
    ProfesorNotifica = models.ForeignKey(Profesores, blank=True, null=True, on_delete=models.SET_NULL, related_name='guardias_notifica')
    ProfesorConfirma = models.ForeignKey(Profesores, blank=True, null=True, on_delete=models.SET_NULL, related_name='guardias_confirma')

    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.ProfesorAusente} - {self.Materia} - {self.Unidad} - {self.Aula} - {self.ProfesoresGuardia} - Día {self.Fecha} Tramo {self.Tramo}"

    class Meta:
        verbose_name = "Item Guardia"
        verbose_name_plural = "Items Guardia"
        unique_together = ('Unidad', 'ProfesorAusente', 'Aula', 'Tarea', 'Materia', 'Fecha', 'Tramo', 'ProfesorNotifica', 'ProfesorConfirma', 'curso_academico')

class TiempoGuardia(models.Model):
    profesor = models.ForeignKey(Profesores, on_delete=models.CASCADE)
    dia_semana = models.IntegerField(choices=[(i, dia) for i, dia in enumerate(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], 1)])
    tramo = models.IntegerField(choices=[(i, f'Tramos {i}h') for i in range(1, 8)])  # Tramos de 1h a 7h
    tiempo_asignado = models.IntegerField()  # Minutos asignados
    item_guardia = models.ForeignKey(ItemGuardia, on_delete=models.CASCADE, related_name="tiempos_guardia")

    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.profesor} - Día {self.dia_semana}, Tramo {self.tramo}: {self.tiempo_asignado} min"

    class Meta:
        unique_together = ('profesor', 'dia_semana', 'tramo', 'tiempo_asignado', 'item_guardia', 'curso_academico')
