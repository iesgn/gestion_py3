from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from centro.models import CursoAcademico
from centro.utils import get_current_academic_year
from reservas.models import Reservas


@receiver(post_save, sender=Reservas)
def asignar_curso_academico(sender, instance, created, **kwargs):
    if created:
        curso_actual = get_current_academic_year()
        instance.curso_academico = curso_actual
        instance.save()