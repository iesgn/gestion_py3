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
from django.conf import settings
from centro.models import CursoAcademico, Centros, Materia, Departamentos, Niveles


class CampanaTransito(models.Model):
    descripcion = models.CharField(max_length=200, verbose_name="Descripción del Proceso")
    curso_academico = models.ForeignKey(CursoAcademico, on_delete=models.CASCADE)
    niveles = models.ManyToManyField(Niveles, verbose_name="Niveles Objetivo", blank=True)
    centros_origen = models.ManyToManyField(Centros, related_name='configuraciones_transito', blank=True)
    materias_implicadas = models.ManyToManyField(Materia, blank=True)
    cerrada = models.BooleanField(default=False)


    class Meta:
        verbose_name = "Campaña de Tránsito"
        verbose_name_plural = "Campañas de Tránsito"

    def __str__(self):
        # Creamos una cadena con los nombres de los niveles (ej: "1º ESO, 2º ESO")
        niveles_str = ", ".join([n.Nombre for n in self.niveles.all()])
        return f"{self.descripcion} ({self.curso_academico}) - [{niveles_str}]"

#  Informe: El análisis específico del departamento
# Equivale a tu 'Resultado'
class InformeDepartamento(models.Model):
    campana = models.ForeignKey(CampanaTransito, on_delete=models.CASCADE, related_name='informes')

    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    centro_origen = models.ForeignKey(Centros, on_delete=models.CASCADE, related_name='informes_recibidos')

    cuestiones_generales = models.TextField(blank=True, null=True, verbose_name="Cuestiones Generales")
    fortalezas = models.TextField(blank=True, null=True, verbose_name="Fortalezas Detectadas")
    debilidades = models.TextField(blank=True, null=True, verbose_name="Debilidades Detectadas")

    class Meta:
        # Integridad: Un mismo departamento no debe evaluar dos veces
        # al mismo centro en la misma campaña.
        unique_together = ['campana', 'materia', 'centro_origen']
        verbose_name = "Informe de Departamento"
        verbose_name_plural = "Informes de Departamento"

    def __str__(self):
        return f"Informe {self.materia} -> {self.centro_origen}"

class AsignacionMateriaDepartamento(models.Model):
    """
    Define qué Departamento es responsable de qué Materia en una Campaña específica.
    Ej: En la Campaña Tránsito 24/25, la materia 'Lengua' la evalúa el Dept. de 'Lengua Castellana'.
    """
    campana = models.ForeignKey(CampanaTransito, on_delete=models.CASCADE, related_name='asignaciones_departamento')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamentos, on_delete=models.CASCADE)

    class Meta:
        # Evitamos duplicados: Una materia solo puede estar asignada a un departamento en una misma campaña
        unique_together = ['campana', 'materia']
        verbose_name = "Asignación Materia-Departamento"
        verbose_name_plural = "Asignaciones Materias-Departamentos"

    def __str__(self):
        return f"{self.materia} -> {self.departamento}"