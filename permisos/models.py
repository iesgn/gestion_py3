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

class AsuntoPropio(models.Model):
    profesor = models.ForeignKey('centro.Profesores', on_delete=models.CASCADE, related_name='asuntos_propios')
    fecha = models.DateField()
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.CASCADE)

    ESTADOS = (
        ('P', 'Pendiente'),
        ('A', 'Aprobado'),
        ('R', 'Rechazado'),
    )
    estado = models.CharField(max_length=1, choices=ESTADOS, default='P')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profesor', 'fecha', 'curso_academico')

    def __str__(self):
        return f"{self.profesor} - {self.fecha} ({self.get_estado_display()})"
