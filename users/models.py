from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.core.validators import FileExtensionValidator

class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('normal', 'Normal User'),
        ('artist', 'Verified Artist'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    followed_artists = models.ManyToManyField('ArtistProfile', related_name='followers', blank=True)
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
    

      # Add analytics fields
    monthly_listeners = models.PositiveIntegerField(default=0)  # Number of monthly listeners
    total_plays = models.PositiveIntegerField(default=0)        # Total plays of all songs
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Total revenue in dollars
    def __str__(self):
        return f"{self.artist_name}'s artist profile"

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
        self.total_tracks = self.songs.count()
        self.save()

    def update_duration(self):
        total_duration = sum(song.duration.total_seconds() for song in self.songs.all() if song.duration)
        self.duration = timedelta(seconds=total_duration)
        self.save()

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
    
    def __str__(self):
        return f"{self.title} by {self.artist.artist_name}"

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

