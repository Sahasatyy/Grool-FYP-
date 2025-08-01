# Generated by Django 5.1.5 on 2025-03-19 10:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_userprofile_followed_artists'),
    ]

    operations = [
        migrations.AddField(
            model_name='artistprofile',
            name='monthly_listeners',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='artistprofile',
            name='total_plays',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='artistprofile',
            name='total_revenue',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
