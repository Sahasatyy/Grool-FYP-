from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import ArtistProfile, UserProfile, Song, Genre, Playlist, Album
from django.core.exceptions import ValidationError

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'})
    )
    password1 = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )
    password2 = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    password = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']

class ArtistVerificationForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['artist_name', 'description_about_yourself', 'social_links', 'popular_songs_1', 'popular_songs_2', 'profile_picture', 'genre', 'bio']

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']

class EditProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)

    class Meta:
        model = UserProfile
        fields = ['bio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

class ChangeEmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

class SongUploadForm(forms.ModelForm):
    MAX_FILE_SIZE = 20 * 1024 * 1024 
    genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.CheckboxSelectMultiple, 
        required=False 
    )

    album = forms.ModelChoiceField(
    queryset=Album.objects.none(),
    required=False,
    label="Select Album"
    )

    class Meta:
        model = Song
        fields = [
            'title', 'album', 'audio_file', 'cover_image', 'genres', 'lyrics', 'duration', 'is_explicit', 'is_public'
        ]

    def __init__(self, *args, **kwargs):
        artist = kwargs.pop('artist', None)
        super().__init__(*args, **kwargs)
        if artist:
            self.fields['album'].queryset = Album.objects.filter(artist=artist)

    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        
        if audio_file:
            if audio_file.size > self.MAX_FILE_SIZE:
                raise ValidationError(f'File too large. Max size is {self.MAX_FILE_SIZE / (1024 * 1024)}MB.')
            
            valid_types = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4']
            content_type = getattr(audio_file, 'content_type', None)
            
            if content_type and content_type not in valid_types:
                raise ValidationError('Unsupported audio file type.')
        
        return audio_file

class PlaylistForm(forms.ModelForm):
    is_public = forms.BooleanField(
        required=False,
        label="Make playlist public",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Playlist
        fields = ['name', 'is_public']  # Only include name and is_public
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter playlist name'
            }),
        }

class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'release_date', 'genre', 'cover_image', 'label', 'description']
        widgets = {
            'release_date': forms.DateInput(attrs={'class': 'flatpickr', 'placeholder': 'Select a date'}),
        }