# Generated by Django 5.1.5 on 2025-03-06 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_artistprofile_bio_alter_song_audio_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='artistprofile',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_pics/'),
        ),
    ]
