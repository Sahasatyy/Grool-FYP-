from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import timedelta
import os



class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('normal', 'Normal User'),
        ('artist', 'Verified Artist'),
        ('premium', 'Premium User'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    followed_artists = models.ManyToManyField('ArtistProfile', related_name='followers', blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='normal')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True)
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def has_active_premium(self):
        if not self.is_premium:
            return False
        if self.premium_expiry and timezone.now() > self.premium_expiry:
            self.is_premium = False
            self.save()
            return False
        return True

def qr_code_upload_path(instance, filename):
    return os.path.join('support_qr_codes', f'user_{instance.user_profile.user.id}', filename)

class ArtistProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='artist_profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Profile Picture",
                                        help_text="Upload a profile picture.")
    artist_name = models.CharField(max_length=100, verbose_name="Artist Name", help_text="Enter your artist name.")
    genre = models.CharField(max_length=50, verbose_name="Genre", help_text="Enter your music genre.")
    verification_date = models.DateField(auto_now_add=True, verbose_name="Verification Date")
    bio = models.TextField(blank=True, verbose_name="Biography", help_text="Tell us about yourself.")
    is_verified = models.BooleanField(default=False, verbose_name="Verified Status")
    description_about_yourself = models.TextField(blank=True, null=True, verbose_name="Description", help_text="Describe yourself in detail.")
    social_links = models.URLField(blank=True, null=True, verbose_name="Social Links", help_text="Provide links to your social media profiles.")
    popular_songs_1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Popular Song 1", help_text="Enter one of your popular songs.")
    popular_songs_2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Popular Song 2", help_text="Enter another popular song.")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    monthly_listeners = models.PositiveIntegerField(default=0)  # Number of monthly listeners
    total_plays = models.PositiveIntegerField(default=0)        # Total plays of all songs
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Total revenue in dollars
    support_qr_code = models.ImageField(
        upload_to=qr_code_upload_path,
        null=True,
        blank=True,
        verbose_name='Support QR Code',
        help_text='Upload a QR code for fans to support you'
    )
    support_message = models.TextField(blank=True, default="")

    merchandise_url = models.URLField(blank=True, null=True, verbose_name="Merchandise URL")
    events_url = models.URLField(blank=True, null=True, verbose_name="Events URL")

    class Meta:
        verbose_name = "Artist Profile"
        verbose_name_plural = "Artist Profiles"
        ordering = ['-verification_date']

    def __str__(self):
        return f"{self.artist_name}'s artist profile"
    
    def followers_count(self):
        return self.followers.count()  # Or use cached_property if needed
    
    def get_monthly_listeners(self):
        """Calculate monthly listeners"""
        # Implement your actual logic here
        return self.monthly_listeners or 0
    
    def get_total_plays(self):
        """Calculate total plays"""
        # Implement your actual logic here
        return self.total_plays or 0
    
    def get_total_revenue(self):
        """Calculate total revenue"""
        # Implement your actual logic here
        return float(self.total_revenue or 0)
    
def save(self, *args, **kwargs):

    try:
        old = ArtistProfile.objects.get(pk=self.pk)
        if old.support_qr_code and old.support_qr_code != self.support_qr_code:
            old.support_qr_code.delete(save=False)
    except ArtistProfile.DoesNotExist:
        pass
    super().save(*args, **kwargs)

class Album(models.Model):
    artist = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=200)
    release_date = models.DateField()
    genre = models.CharField(max_length=100, default="Unknown")  # Add default value
    cover_image = models.ImageField(upload_to='album_covers/', blank=True, null=True)
    label = models.CharField(max_length=200, blank=True, null=True)
    total_tracks = models.PositiveIntegerField(default=0)
    duration = models.DurationField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def update_total_tracks(self):
        """Update the total tracks count"""
        self.total_tracks = self.songs.count()
        self.save(update_fields=['total_tracks'])
    
    def update_duration(self):
        """Update the total duration"""
        total_seconds = sum(
            song.duration.total_seconds() 
            for song in self.songs.all() 
            if song.duration
        )
        self.duration = timedelta(seconds=total_seconds)
        self.save(update_fields=['duration'])
    
    def get_artist_songs_not_in_album(self):
        return Song.objects.filter(artist=self.artist).exclude(album=self)

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE, related_name='songs')
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='songs')
    audio_file = models.FileField(
        upload_to='songs/', 
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])],
    )
    cover_image = models.ImageField(upload_to='song_covers/', blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    release_date = models.DateField(auto_now_add=True)
    genres = models.ManyToManyField(Genre, blank=True)
    lyrics = models.TextField(blank=True)
    is_explicit = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    total_listens = models.PositiveIntegerField(default=0) 

    play_duration = models.DurationField(default=timedelta(0))  # Total play time across all users
    qualified_plays = models.PositiveIntegerField(default=0)  # Count of plays >1 minute
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    revenue_updated_at = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"{self.title} by {self.artist.artist_name}"

class PlayHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    play_start = models.DateTimeField(auto_now_add=True)
    play_duration = models.DurationField()
    qualified = models.BooleanField(default=False)  

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'song')  # Ensure a user can't favorite the same song twice

class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=255)
    songs = models.ManyToManyField(Song, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('artist_pro', 'Artist Pro'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    features = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
        
    def __str__(self):
        return f"{self.name} (Rs. {self.price}/month)"

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    khalti_idx = models.CharField(max_length=100, blank=True)
    payment_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-start_date']
    

    def save(self, *args, **kwargs):
        if not self.pk:  # New subscription
            self.end_date = timezone.now() + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.end_date
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
class PremiumAd(models.Model):
    title = models.CharField(max_length=100, default="Upgrade to Premium")
    audio_file = models.FileField(upload_to='ads/')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
class RevenueRecord(models.Model):
    artist = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    plays_count = models.PositiveIntegerField()
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-calculated_at']
        verbose_name = "Revenue Record"
        verbose_name_plural = "Revenue Records"