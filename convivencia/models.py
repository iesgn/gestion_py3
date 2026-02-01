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

from datetime import datetime, date
from django.db import models
from django.utils import timezone


# Create your models here.
# from centro.models import Alumnos, Profesores, CursoAcademico

TRAMOS_HORARIOS = (
    ('1','Primera (1ª)'),
    ('2','Segunda (2ª)'),
    ('3','Tercera (3ª)'),
    ('4','Recreo (REC)'),
    ('5','Cuarta (4ª)'),
    ('6','Quinta (5ª)'),
    ('7','Sexta (6ª)'),
)

MEDIOS_CONTACTO = (
		('1', 'Teléfono'),
		('2', 'PASEN (Observaciones compartidas)'),
	)

# Register your models here.

class TiposAmonestaciones(models.Model):
	TipoAmonestacion = models.CharField(max_length=60)
	TipoFalta = models.CharField(max_length=1, default='L')

	def __str__(self):
		return "("+self.TipoFalta+") "+self.TipoAmonestacion

	class Meta:
		verbose_name="Tipo Amonestación"
		verbose_name_plural="Tipos de Amonestaciones"

class Amonestaciones(models.Model):

	IdAlumno = models.ForeignKey('centro.Alumnos', related_name='amonestaciones',null=True,on_delete=models.SET_NULL)
	Fecha = models.DateField()
	Hora = models.CharField(max_length=1,choices=TRAMOS_HORARIOS,default='1')
	Profesor = models.ForeignKey('centro.Profesores', null=True, on_delete=models.SET_NULL)
	Tipo = models.ForeignKey(TiposAmonestaciones, related_name='Tipo_de', blank=True, null=True,
							 on_delete=models.SET_NULL)
	Comentario=models.TextField(blank=True)
	Enviado = models.BooleanField(default=False,verbose_name="Enviar por correo electrónico")

	DerivadoConvivencia = models.BooleanField(default=False, verbose_name="Derivado a Aula Horizonte")

	ComunicadoFamilia = models.BooleanField(default=False, verbose_name="Comunicado a la familia")
	FamiliarComunicado = models.TextField(blank=True, null=True)
	FechaComunicado = models.DateField(blank=True, null=True)
	HoraComunicado = models.TimeField(blank=True, null=True)
	Medio = models.CharField(max_length=1, choices=MEDIOS_CONTACTO,blank=True, null=True)
	TelefonoComunicado = models.TextField(blank=True, null=True)
	ObservacionComunicado = models.TextField(blank=True, null=True)

	curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

	def __str__(self):
		return self.IdAlumno.Nombre

	@property
	def caducada(self):
		hoy = datetime.now().date()  # Obtener la fecha de hoy

		diferencia = hoy - self.Fecha


		if self.gravedad == "Leve":
			return diferencia.days > 30
		elif self.gravedad == "Grave":
			return diferencia.days > 60
		else:
			return False

	@property
	def sancionada(self):
		ultima_sancion = Sanciones.objects.filter(IdAlumno=self.IdAlumno).order_by("Fecha").last()
		if ultima_sancion:
			return self.Fecha <= ultima_sancion.Fecha
		else:
			return False

	@property
	def gravedad(self):
		if self.Tipo and self.Tipo.TipoFalta:
			if self.Tipo.TipoFalta == "L":
				return "Leve"
			elif self.Tipo.TipoFalta == "G":
				return "Grave"
		return "Desconocida"  # Valor por defecto si Tipo o TipoFalta es None

	@property
	def vigente(self):
		return (not self.caducada) and (not self.sancionada)

	class Meta:
		verbose_name="Amonestación"
		verbose_name_plural="Amonestaciones"
		unique_together = ('IdAlumno', 'Fecha', 'Hora', 'Profesor', 'Tipo', 'Comentario', 'DerivadoConvivencia', 'FamiliarComunicado', 'FechaComunicado', 'HoraComunicado', 'Medio', 'TelefonoComunicado', 'ObservacionComunicado', 'curso_academico')


class Sanciones(models.Model):
	
	IdAlumno = models.ForeignKey('centro.Alumnos',null=True,on_delete=models.SET_NULL)
	Fecha = models.DateField()
	Fecha_fin = models.DateField(verbose_name="Fecha finalización")
	Sancion=models.CharField(max_length=100,blank=True)
	Comentario=models.TextField(blank=True)
	NoExpulsion = models.BooleanField(default=False,verbose_name="Medidas de flexibilización a la expulsión")

	curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

	def __str__(self):
		return self.IdAlumno.Nombre 

	class Meta:
		verbose_name="Sanción"
		verbose_name_plural="Sanciones"
		unique_together = ('IdAlumno', 'Fecha', 'Fecha_fin', 'Sancion', 'Comentario', 'curso_academico')


class PropuestasSancion(models.Model):
	curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

	alumno = models.ForeignKey('centro.Alumnos',null=True,on_delete=models.SET_NULL)
	entrada = models.DateField()
	salida = models.DateField(blank=True, null=True)
	motivo_salida = models.TextField(blank=True, null=True)
	amonestaciones = models.ManyToManyField(Amonestaciones, 'propuestas_sancion', null=True, blank=True)
	ignorar = models.BooleanField(default=False)

	leves = models.PositiveSmallIntegerField(default=0)
	graves = models.PositiveSmallIntegerField(default=0)
	peso = models.PositiveSmallIntegerField(default=0)


	def __str__(self):
		return f"Propuesta de sanción de {self.alumno} ({self.alumno.leves} leves, {self.alumno.graves} graves - peso: {self.alumno.peso_amonestaciones}"

	class Meta:
		verbose_name = "Propuesta de alumnado sancionable"
		verbose_name_plural = "Propuestas de alumnado sancionable"



class IntervencionAulaHorizonte(models.Model):
	alumno = models.ForeignKey('centro.Alumnos', on_delete=models.CASCADE, related_name='registros_aula_horizonte')
	profesor_atiende = models.ForeignKey('centro.Profesores', on_delete=models.SET_NULL, null=True, related_name='atiende_aula_horizonte')
	profesor_envia = models.ForeignKey('centro.Profesores', on_delete=models.SET_NULL, null=True, related_name='envia_aula_horizonte')
	fecha = models.DateField()
	tramo_horario = models.CharField(max_length=1, choices=TRAMOS_HORARIOS)
	tarea_asignada = models.TextField(help_text="Descripción de la tarea que debía realizar el alumno/a.")
	tarea_realizada = models.TextField(blank=True, help_text="Trabajo realizado efectivamente durante la intervención.")
	motivo = models.TextField(help_text="Motivo de la derivación. Conducta observada.")
	reflexion_alumno = models.TextField(blank=True, help_text="Reflexión escrita o verbal del alumno/a (si la hubo).")
	necesita_reubicacion = models.BooleanField(default=False, help_text="¿Fue necesario ubicar al alumno/a en otro grupo?")
	grupo_destino = models.ForeignKey('centro.Cursos', on_delete=models.SET_NULL, null=True, blank=True, related_name='destino_aula_horizonte')
	observaciones = models.TextField(blank=True)
	creada_por = models.ForeignKey('centro.Profesores', on_delete=models.SET_NULL, null=True, related_name='intervenciones_creadas')
	creado_en = models.DateTimeField(auto_now_add=True)
	curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)


	class Meta:
		verbose_name = "Registro del Aula Horizonte"
		verbose_name_plural = "Registros del Aula Horizonte"
		ordering = ['-fecha', 'tramo_horario']


	def __str__(self):
		return f"{self.fecha} - {self.alumno} atendido por {self.profesor_atiende}"