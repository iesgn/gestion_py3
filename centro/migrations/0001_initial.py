# Generated by Django 4.2.7 on 2024-09-15 08:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Aulas',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Aula', models.CharField(max_length=30)),
            ],
            options={
                'verbose_name': 'Aula',
                'verbose_name_plural': 'Aulas',
            },
        ),
        migrations.CreateModel(
            name='CursoAcademico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('año_inicio', models.IntegerField(blank=True, null=True)),
                ('año_fin', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Departamentos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Abr', models.CharField(max_length=4)),
                ('Nombre', models.CharField(max_length=30)),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
            },
        ),
        migrations.CreateModel(
            name='Niveles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Nombre', models.CharField(max_length=255)),
                ('Abr', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'Nivel',
                'verbose_name_plural': 'Niveles',
            },
        ),
        migrations.CreateModel(
            name='Profesores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Nombre', models.CharField(max_length=20)),
                ('Apellidos', models.CharField(max_length=30)),
                ('DNI', models.CharField(blank=True, max_length=10)),
                ('Telefono', models.CharField(blank=True, max_length=9)),
                ('Movil', models.CharField(blank=True, max_length=9)),
                ('Email', models.EmailField(max_length=254)),
                ('Baja', models.BooleanField(default=False)),
                ('password_changed', models.BooleanField(default=False)),
                ('Departamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.departamentos')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profesor', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Profesor',
                'verbose_name_plural': 'Profesores',
                'ordering': ('Apellidos',),
            },
        ),
        migrations.CreateModel(
            name='Cursos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Curso', models.CharField(max_length=30)),
                ('Abe', models.CharField(blank=True, max_length=10, null=True)),
                ('Aula', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='Curso', to='centro.aulas')),
                ('EquipoEducativo', models.ManyToManyField(blank=True, to='centro.profesores', verbose_name='Equipo Educativo')),
                ('Nivel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='Nivel', to='centro.niveles')),
                ('Tutor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='Tutor_de', to='centro.profesores')),
            ],
            options={
                'verbose_name': 'Curso',
                'verbose_name_plural': 'Cursos',
            },
        ),
        migrations.CreateModel(
            name='Areas',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Nombre', models.CharField(max_length=30)),
                ('Departamentos', models.ManyToManyField(blank=True, to='centro.departamentos')),
            ],
            options={
                'verbose_name': 'Área',
                'verbose_name_plural': 'Áreas',
            },
        ),
        migrations.CreateModel(
            name='Alumnos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Nombre', models.CharField(max_length=50)),
                ('NIE', models.CharField(blank=True, max_length=20, null=True)),
                ('DNI', models.CharField(blank=True, max_length=10, null=True)),
                ('Direccion', models.CharField(max_length=60)),
                ('CodPostal', models.CharField(max_length=5, verbose_name='Código postal')),
                ('Localidad', models.CharField(max_length=30)),
                ('Fecha_nacimiento', models.DateField(verbose_name='Fecha de nacimiento')),
                ('Provincia', models.CharField(max_length=30)),
                ('Ap1tutor', models.CharField(max_length=20, verbose_name='Apellido 1 Tutor')),
                ('Ap2tutor', models.CharField(max_length=20, verbose_name='Apellido 2 Tutor')),
                ('Nomtutor', models.CharField(max_length=20, verbose_name='Nombre tutor')),
                ('Telefono1', models.CharField(blank=True, max_length=12)),
                ('Telefono2', models.CharField(blank=True, max_length=12)),
                ('email', models.EmailField(blank=True, max_length=70)),
                ('Obs', models.TextField(blank=True, verbose_name='Observaciones')),
                ('Unidad', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.cursos')),
            ],
            options={
                'verbose_name': 'Alumno',
                'verbose_name_plural': 'Alumnos',
            },
        ),
    ]
