# Generated by Django 4.2.7 on 2024-12-08 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('convivencia', '0004_propuestassancion_graves_propuestassancion_leves_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='propuestassancion',
            name='ultima_amonestacion',
        ),
        migrations.AddField(
            model_name='propuestassancion',
            name='amonestaciones',
            field=models.ManyToManyField(blank=True, null=True, related_name='propuestas_sancion', to='convivencia.amonestaciones'),
        ),
    ]
