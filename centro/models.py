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


from datetime import date

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from .utils import get_current_academic_year
# from fusiona_old_bbdd import curso_academico_id
from gestion import settings


# Create your models here.

class CursoAcademico(models.Model):
    nombre = models.CharField(max_length=100)
    año_inicio = models.IntegerField(null=True,blank=True)
    año_fin = models.IntegerField(null=True,blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.año_inicio}-{self.año_fin})"

    def __sub__(self, other):
        if isinstance(other, int):
            inicio = self.año_inicio - other
            return CursoAcademico.objects.filter(año_inicio=inicio).first()
        else:
            raise NotImplementedError


class Aulas(models.Model):
    Aula = models.CharField(max_length=30)
    AulaHorarios = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.Aula

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"


class Departamentos(models.Model):
    Abr = models.CharField(max_length=4)
    Nombre = models.CharField(max_length=30)

    def __str__(self):
        return self.Nombre

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"


class Areas(models.Model):
    Nombre = models.CharField(max_length=30)
    Departamentos = models.ManyToManyField(Departamentos, blank=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"


class Profesores(models.Model):
    # Curro Jul 24: Anado user para vincular Profesor con user de la web
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='profesor')
    Nombre = models.CharField(max_length=20)
    Apellidos = models.CharField(max_length=30)
    DNI = models.CharField(max_length=10, blank=True)
    Telefono = models.CharField(max_length=9, blank=True)
    Movil = models.CharField(max_length=9, blank=True)
    Email = models.EmailField()
    Departamento = models.ForeignKey(Departamentos, blank=True, null=True, on_delete=models.SET_NULL)
    Baja = models.BooleanField(default=False)
    password_changed = models.BooleanField(default=False)  # Nuevo campo
    NombreHorarios = models.CharField(max_length=200, blank=True, null=True)
    SustitutoDe = models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='sustitutos',verbose_name="Sustituto de")


    # Curro Jul 24: Anado la coma entre los apellidos y el nombre
    def __str__(self):
        return self.Apellidos + ", " + self.Nombre

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"
        ordering = ("Apellidos",)

    @property
    def nombre_completo(self):
        return self.Apellidos + ", " + self.Nombre


class Niveles(models.Model):
    Nombre = models.CharField(max_length=255)
    Abr = models.CharField(max_length=50)
    NombresAntiguos = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.Nombre

    class Meta:
        verbose_name = "Nivel"
        verbose_name_plural = "Niveles"

class CursosActivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(Activo=True).order_by('Orden', 'id')

class Cursos(models.Model):
    Curso = models.CharField(max_length=30)
    Tutor = models.ForeignKey(Profesores, related_name='Tutor_de', blank=True, null=True, on_delete=models.SET_NULL)
    Abe = models.CharField(max_length=10, blank=True, null=True)
    Nivel = models.ForeignKey(Niveles, related_name='Nivel', blank=True, null=True, on_delete=models.SET_NULL)
    Aula = models.ForeignKey(Aulas, related_name='Curso', blank=True, null=True, on_delete=models.SET_NULL)
    CursoHorarios = models.CharField(max_length=100, blank=True, null=True)
    Dificultad = models.IntegerField(blank=True, null=True)
    Activo = models.BooleanField(default=True)
    Orden = models.PositiveIntegerField(default=0)  # Campo para controlar el orden

    # Managers
    all_objects = models.Manager()          # sin filtro (útil para administración/tareas)
    objects = CursosActivosManager()        # por defecto: solo Activo=True

    def __str__(self):
        return self.Curso

    def __lt__(self, other):
        # Comparar los cursos según su 'id' o el campo que prefieras para la ordenación
        if isinstance(other, Cursos):
            return self.id < other.id
        return NotImplemented

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['Orden', 'id']
        # Importante para que Django use el manager sin filtro en tareas internas
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'


class Alumnos(models.Model):
    Nombre = models.CharField(max_length=50)
    NIE = models.CharField(max_length=20, blank=True, null=True)
    DNI = models.CharField(max_length=10, blank=True, null=True)
    Direccion = models.CharField(max_length=60)
    CodPostal = models.CharField(max_length=5, verbose_name="Código postal")
    Localidad = models.CharField(max_length=30)
    Fecha_nacimiento = models.DateField('Fecha de nacimiento')
    Provincia = models.CharField(max_length=30)
    Unidad = models.ForeignKey(Cursos, blank=True, null=True, on_delete=models.SET_NULL)
    Ap1tutor = models.CharField(max_length=20, verbose_name="Apellido 1 Tutor")
    Ap2tutor = models.CharField(max_length=20, verbose_name="Apellido 2 Tutor")
    Nomtutor = models.CharField(max_length=20, verbose_name="Nombre tutor")
    Telefono1 = models.CharField(max_length=12, blank=True)
    Telefono2 = models.CharField(max_length=12, blank=True)
    email = models.EmailField(max_length=70, blank=True)
    Obs = models.TextField(blank=True, verbose_name="Observaciones")
    PDC = models.BooleanField(default=False)
    NEAE = models.BooleanField(default=False)
    Centro_EP = models.ForeignKey('centro.Centros', related_name='alumnado_ESO', on_delete=models.SET_NULL, null=True, blank=True)
    Centro_ESO = models.ForeignKey('centro.Centros', related_name='alumnado_BTOCF', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        dni = self.DNI if self.DNI else "Sin DNI"
        return dni + " - " + self.Nombre

    @property
    def amonestaciones_leves_vigentes(self):
        return [am for am in self.amonestaciones.order_by("Fecha").all() if am.gravedad == "Leve" and am.vigente]

    @property
    def amonestaciones_graves_vigentes(self):
        return [am for am in self.amonestaciones.order_by("Fecha").all() if am.gravedad == "Grave" and am.vigente]

    @property
    def amonestaciones_vigentes(self):
        return [am for am in self.amonestaciones.order_by("Fecha").all() if am.vigente]

    @property
    def leves(self):
        return len(self.amonestaciones_leves_vigentes)

    @property
    def graves(self):
        return len(self.amonestaciones_graves_vigentes)

    @property
    def sancionable(self):
        return self.peso_amonestaciones >= 4

    @property
    def peso_amonestaciones(self):
        return self.leves + 2 * self.graves

    @property
    def ultima_sancion(self):
        return self.sanciones_set.order_by("Fecha").last()

    def edad(self, curso_academico):
        fecha_final = date(curso_academico.año_fin, 12, 31)
        return (fecha_final - self.Fecha_nacimiento).years

    @property
    def edad_actual(self):
        hoy = date.today()
        nacimiento = self.Fecha_nacimiento
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return edad

    class Meta:
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

class Centros(models.Model):
    Codigo = models.CharField(max_length=8, blank=True, null=True)
    Nombre = models.CharField(max_length=50, blank=True, null=True)
    Compensatoria = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Centro"
        verbose_name_plural = "Centros"
        unique_together = ("Codigo", "Nombre")

    def __str__(self):
        return f"{self.Nombre} ({self.Codigo})"

class InfoAlumnos(models.Model):
    C_SEXO = (
        ('H', 'Hombre'),
        ('M', 'Mujer'),
    )
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)
    Alumno = models.ForeignKey('centro.Alumnos', related_name='info_adicional', null=True, on_delete=models.SET_NULL)
    Nivel = models.ForeignKey(Niveles, related_name='InfoNivel', blank=True, null=True, on_delete=models.SET_NULL)
    Unidad = models.CharField(max_length=20, verbose_name="Unidad", null=True, blank=True)
    Repetidor = models.BooleanField(default=False)
    Edad = models.PositiveSmallIntegerField(default=0)
    Sexo = models.CharField(max_length=1, verbose_name="Sexo", choices=C_SEXO, null=True, blank=True)
    CentroOrigen = models.ForeignKey('centro.Centros', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Información Adicional de un Alumno"
        verbose_name_plural = "Información Adicional del Alumnado"
        unique_together = ('curso_academico', 'Alumno')


class Materia(models.Model):
    nombre = models.CharField(max_length=100)  # Nombre completo de la materia
    abr = models.CharField(max_length=20, blank=True)                  # Abreviatura (ej. "MAT")
    nombre_horarios = models.CharField(max_length=100, blank=True)  # Para uso futuro en horarios
    horas = models.PositiveSmallIntegerField(default=0)    # Número de horas semanales
    nivel = models.ForeignKey('Niveles', on_delete=models.CASCADE)  # Nivel educativo (1º ESO, etc.)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.abr} - {self.nombre} ({self.nivel.Abr})"

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ['nivel__Abr', 'abr']

class MateriaImpartida(models.Model):
    profesor = models.ForeignKey(Profesores, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    curso = models.ForeignKey(Cursos, on_delete=models.CASCADE)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.profesor} imparte {self.materia} en {self.curso}"

    class Meta:
        verbose_name = "Materia impartida"
        verbose_name_plural = "Materias impartidas"
        unique_together = ('profesor', 'materia', 'curso')
        ordering = ['curso__Nivel__Abr', 'curso__Curso', 'materia__abr']

class MatriculaMateria(models.Model):
    alumno = models.ForeignKey(Alumnos, on_delete=models.CASCADE)
    materia_impartida = models.ForeignKey(MateriaImpartida, on_delete=models.CASCADE)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.alumno.Nombre} matriculado en {self.materia_impartida.materia.nombre} ({self.materia_impartida.curso})"

    class Meta:
        verbose_name = "Matrícula de materia"
        verbose_name_plural = "Matrículas de materias"
        unique_together = ('alumno', 'materia_impartida')


class LibroTexto(models.Model):
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE, related_name='libros')
    nivel = models.ForeignKey('Niveles', on_delete=models.CASCADE, related_name='libros_texto')

    isbn = models.CharField("ISBN/EAN", max_length=20, blank=True)
    editorial = models.CharField(max_length=200, blank=True)
    titulo = models.CharField(max_length=300, blank=True)
    anyo_implantacion = models.PositiveIntegerField(null=True, blank=True)
    importe_estimado = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    es_digital = models.BooleanField(default=False)
    incluir_en_cheque_libro = models.BooleanField(default=False)
    es_otro_material = models.BooleanField(default=False)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.titulo or 'Sin título'}"


class MomentoRevisionLibros(models.Model):
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)
    estados = models.ManyToManyField('EstadoLibro', related_name='momentos')

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.nombre

class EstadoLibro(models.Model):
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.nombre

class RevisionLibro(models.Model):
    profesor = models.ForeignKey('Profesores', on_delete=models.CASCADE)
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE)
    curso = models.ForeignKey('Cursos', on_delete=models.CASCADE)
    libro = models.ForeignKey('LibroTexto', on_delete=models.CASCADE)
    momento = models.ForeignKey('MomentoRevisionLibros', on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('profesor', 'curso', 'materia', 'libro', 'momento', 'fecha', 'curso_academico')

    def __str__(self):
        return f"{self.profesor} - {self.curso} - {self.º} - {self.libro} - {self.momento} ({self.fecha})"

class RevisionLibroAlumno(models.Model):
    revision = models.ForeignKey('RevisionLibro', on_delete=models.CASCADE, related_name='detalles')
    alumno = models.ForeignKey('Alumnos', on_delete=models.CASCADE)
    estado = models.ForeignKey('EstadoLibro', on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ('revision', 'alumno')

    def __str__(self):
        return f"{self.revision} - {self.alumno} - {self.estado} ({self.observaciones})"


class PreferenciaHorario(models.Model):
    profesor = models.OneToOneField(Profesores, on_delete=models.CASCADE, related_name='preferencia_horaria')

    curso_academico = models.ForeignKey('centro.CursoAcademico', on_delete=models.SET_NULL, null=True, blank=True)

    # Guardamos la información del horario como JSON
    horario = models.JSONField(default=dict)  # Ejemplo: {'Lunes-1': True, 'Martes-2': False, ...}
    flexibilidad_inicio = models.BooleanField(default=False)
    flexibilidad_fin = models.BooleanField(default=False)

    guardias = models.JSONField(default=list)  # ['Pasillo', 'Recreo', 'Horizonte'], en orden
    observaciones = models.TextField(blank=True)

    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferencias de {self.profesor}"

