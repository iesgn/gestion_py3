# Generated by Django 4.2.7 on 2024-08-15 12:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('centro', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TiposAmonestaciones',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('TipoAmonestacion', models.CharField(max_length=60)),
                ('TipoFalta', models.CharField(default='L', max_length=1)),
            ],
            options={
                'verbose_name': 'Tipo Amonestación',
                'verbose_name_plural': 'Tipos de Amonestaciones',
            },
        ),
        migrations.CreateModel(
            name='Sanciones',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Fecha', models.DateField()),
                ('Fecha_fin', models.DateField(verbose_name='Fecha finalización')),
                ('Sancion', models.CharField(blank=True, max_length=100)),
                ('Comentario', models.TextField(blank=True)),
                ('NoExpulsion', models.BooleanField(default=False, verbose_name='Medidas de flexibilización a la expulsión')),
                ('IdAlumno', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.alumnos')),
                ('curso_academico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.cursoacademico')),
            ],
            options={
                'verbose_name': 'Sanción',
                'verbose_name_plural': 'Sanciones',
            },
        ),
        migrations.CreateModel(
            name='Amonestaciones',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Fecha', models.DateField()),
                ('Hora', models.CharField(choices=[('1', 'Primera (1ª)'), ('2', 'Segunda (2ª)'), ('3', 'Tercera (3ª)'), ('4', 'Recreo (REC)'), ('5', 'Cuarta (4ª)'), ('6', 'Quinta (5ª)'), ('7', 'Sexta (6ª)')], default='1', max_length=1)),
                ('Comentario', models.TextField(blank=True)),
                ('Enviado', models.BooleanField(default=False, verbose_name='Enviar por correo electrónico')),
                ('ComunicadoFamilia', models.BooleanField(default=False, verbose_name='Comunicado a la familia')),
                ('FamiliarComunicado', models.TextField(blank=True, null=True)),
                ('FechaComunicado', models.DateField(blank=True, null=True)),
                ('HoraComunicado', models.TimeField(blank=True, null=True)),
                ('Medio', models.CharField(blank=True, choices=[('1', 'Teléfono'), ('2', 'PASEN'), ('3', 'Otro')], max_length=1, null=True)),
                ('TelefonoComunicado', models.TextField(blank=True, null=True)),
                ('ObservacionComunicado', models.TextField(blank=True, null=True)),
                ('IdAlumno', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.alumnos')),
                ('Profesor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.profesores')),
                ('Tipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='Tipo_de', to='convivencia.tiposamonestaciones')),
                ('curso_academico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='centro.cursoacademico')),
            ],
            options={
                'verbose_name': 'Amonestación',
                'verbose_name_plural': 'Amonestaciones',
            },
        ),
    ]
