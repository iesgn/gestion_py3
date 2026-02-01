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

class Calificaciones(models.Model):
    convocatorias = (
        ('EVI', 'Evaluación inicial'),
        ('1EV', '1ª Evaluación'),
        ('2EV', '2ª Evaluacion'),
        ('3EV', '3ª Evaluacion'),
        ('FFP', 'Final FP'),
        ('Ord', 'Ordinaria'),
        ('Ext', 'Extraordinaria')
    )
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)
    Nivel = models.ForeignKey('centro.Niveles', related_name='NivelCalificaciones', blank=True, null=True, on_delete=models.SET_NULL)
    Alumno = models.ForeignKey('centro.Alumnos', on_delete=models.SET_NULL, null=True)
    Convocatoria = models.CharField(max_length=3, choices=convocatorias, default='1EV')
    Materia = models.CharField(max_length=20)
    Calificacion = models.CharField(max_length=10, null=True, blank=True)


    class Meta:
        verbose_name = 'Calificaciones'
        verbose_name_plural = 'Calificaciones'
        unique_together = ('Alumno', 'Convocatoria', 'Materia', 'curso_academico')

    def __str__(self):
        return f"{self.Alumno}({self.curso_academico} - {self.Convocatoria}): {self.Materia} = {self.Calificacion}"


class IndicadoresAlumnado(models.Model):
    convocatorias = (
            ('EVI', 'Evaluación inicial'),
            ('1EV', '1ª Evaluación'),
            ('2EV', '2ª Evaluacion'),
            ('3EV', '3ª Evaluacion'),
            ('FFP', 'Final FP'),
            ('Ord', 'Ordinaria'),
            ('Ext', 'Extraordinaria')
    )
    Alumno = models.ForeignKey('centro.Alumnos', related_name='indicadores', on_delete=models.SET_NULL, null=True)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)
    Convocatoria = models.CharField(max_length=3, choices=convocatorias, default='1EV')
    EstimacionPromocion = models.BooleanField(default=None, null=True, blank=True)
    EficaciaTransito = models.BooleanField(default=None, null=True, blank=True)
    EvaluacionPositivaTodo = models.BooleanField(default=None, null=True, blank=True)
    EficaciaRepeticion = models.BooleanField(default=None, null=True, blank=True)
    IdoneidadCursoEdad = models.BooleanField(default=None, null=True, blank=True)
    AbandonoEscolar = models.BooleanField(default=None, null=True, blank=True)
    Modalidad = models.CharField(max_length=10, null=True, blank=True)
    Promocion = models.BooleanField(default=None, null=True, blank=True)

    class Meta:
        verbose_name = 'Indicadores del Alumnado'
        verbose_name_plural = 'Indicadores del Alumnado'
        unique_together = ('curso_academico', 'Alumno', 'Convocatoria')

    def __str__(self):
        return f"Indicadores del alumno: {self.Alumno} ({self.curso_academico}) - {self.Convocatoria}"

