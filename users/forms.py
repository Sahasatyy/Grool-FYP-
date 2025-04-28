from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import ArtistProfile, UserProfile, Song, Genre, Playlist, Album
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
import random

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

    confirmation_code = forms.CharField(
    required=False,
    widget=forms.HiddenInput()
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
    
    def generate_confirmation_code(self):
        return str(random.randint(100000, 999999))

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
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Song
        fields = [
            'title', 'album', 'audio_file', 'cover_image', 
            'genres', 'lyrics', 'duration', 'is_explicit', 'is_public'
        ]
        widgets = {
            'album': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        self.artist = kwargs.pop('artist', None)  # Get artist from kwargs
        super().__init__(*args, **kwargs)
        
        # Filter albums to only those by this artist
        if self.artist:
            self.fields['album'].queryset = Album.objects.filter(artist=self.artist)
        else:
            self.fields['album'].queryset = Album.objects.none()
            
        # Set empty label for album dropdown
        self.fields['album'].empty_label = "Select an album (optional)"
        self.fields['album'].required = False

    def clean_audio_file(self):
        audio = self.cleaned_data.get('audio_file')

        if audio:
            if not audio.name.lower().endswith('.mp3'):
                raise forms.ValidationError('Only MP3 files are allowed.')
            # Optionally you can also check content_type
            if audio.content_type != 'audio/mpeg':
                raise forms.ValidationError('Invalid audio file type. Must be MP3.')

        return audio

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
    
from .models import SubscriptionPlan

class SubscriptionForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.all(),
        widget=forms.RadioSelect,
        empty_label=None
    )

class SupportQRForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['support_qr_code']
        widgets = {
            'support_qr_code': forms.FileInput(attrs={
                'accept': 'image/png, image/jpeg',
                'class': 'form-control'
            })
        }
        labels = {
            'support_qr_code': 'Support QR Code'
        }
