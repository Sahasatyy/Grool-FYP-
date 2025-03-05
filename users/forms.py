from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import ArtistProfile, Song
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
        fields = ['artist_name', 'genre']

class SongUploadForm(forms.ModelForm):
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    class Meta:
        model = Song
        fields = [
            'title', 'album', 'audio_file', 'cover_image', 'genre', 'lyrics', 'duration', 'is_explicit', 'is_public'
        ]

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