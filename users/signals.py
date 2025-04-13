# signals.py
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, Song, RevenueRecord

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=Song)
def update_song_revenue(sender, instance, **kwargs):
    if instance.total_listens > 0:
        # Calculate new revenue (Rs. 100 per 1000 plays)
        new_revenue = (instance.total_listens // 1000) * 100
        if new_revenue != instance.revenue:
            instance.revenue = new_revenue
            # Avoid recursive save
            Song.objects.filter(pk=instance.pk).update(revenue=new_revenue)
            
            # Create revenue record
            RevenueRecord.objects.create(
                artist=instance.artist,
                song=instance,
                amount=new_revenue - instance.revenue,
                views_count=instance.total_listens
            )

from django.db.models.signals import pre_delete

@receiver(pre_delete, sender=Song)
def preserve_revenue_records(sender, instance, **kwargs):
    # Update artist's total revenue before song is deleted
    instance.artist.total_revenue -= instance.revenue
    instance.artist.save()