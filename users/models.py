from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('normal', 'Normal User'),
        ('artist', 'Verified Artist'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='normal')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class ArtistProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='artist_profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    artist_name = models.CharField(max_length=100)
    genre = models.CharField(max_length=50)
    verification_date = models.DateField(auto_now_add=True)
    bio = models.TextField(blank=True) 
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.artist_name}'s artist profile"

class Album(models.Model):
    artist = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=200)
    release_date = models.DateField()
    cover_image = models.ImageField(upload_to='album_covers/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} by {self.artist.artist_name}"

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
        help_text="Allowed formats: MP3, WAV, OGG, M4A"
    )
    cover_image = models.ImageField(upload_to='song_covers/', blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    release_date = models.DateField(auto_now_add=True)
    genres = models.ManyToManyField(Genre, blank=True)
    lyrics = models.TextField(blank=True)
    is_explicit = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} by {self.artist.artist_name}"

