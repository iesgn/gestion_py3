# Generated by Django 4.2.7 on 2025-01-01 10:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('centro', '0012_remove_materias_grupomateria_remove_materias_nivel_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InfoAlumnos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Unidad', models.CharField(blank=True, max_length=20, null=True, verbose_name='Unidad')),
                ('Repetidor', models.BooleanField(default=False)),
                ('Edad', models.PositiveSmallIntegerField(default=0)),
                ('Sexo', models.CharField(blank=True, choices=[('H', 'Hombre'), ('M', 'Mujer')], max_length=1, null=True, verbose_name='Sexo')),
                ('Alumno', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.alumnos')),
                ('curso_academico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.cursoacademico')),
            ],
            options={
                'verbose_name': 'Información Adicional de un Alumno',
                'verbose_name_plural': 'Información Adicional del Alumnado',
                'unique_together': {('curso_academico', 'Alumno')},
            },
        ),
    ]
