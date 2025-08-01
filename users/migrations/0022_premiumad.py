# Generated by Django 5.1.5 on 2025-04-02 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_alter_subscriptionplan_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='PremiumAd',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Upgrade to Premium', max_length=100)),
                ('audio_file', models.FileField(upload_to='ads/')),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
    ]
