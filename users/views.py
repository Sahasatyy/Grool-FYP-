# Imports

from django.contrib import messages
from django.views import View
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from .forms import RegisterForm, LoginForm, ArtistVerificationForm, SongUploadForm
from .models import ArtistProfile, UserProfile, Song


def home(request):
    songs = Song.objects.filter(is_public=True).select_related('artist')
    return render(request, 'users/home.html', {'songs': songs})


class RegisterView(View):
    form_class = RegisterForm
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_navbar'] = True
        return context


@login_required
def profile_view(request):
    if request.user.profile.user_type == 'artist':
        return redirect('artist_profile')
    return redirect('user_profile')


@login_required
def normal_profile(request):
    user_profile = request.user.profile
    has_artist_request = ArtistProfile.objects.filter(user_profile=user_profile, is_verified=False).exists()
    return render(request, 'users/user_profile.html', {'user_profile': user_profile, 'has_artist_request': has_artist_request})


@login_required
def artist_profile(request):
    user_profile = request.user.profile
    if user_profile.user_type != 'artist':
        messages.error(request, "You don't have artist privileges yet.")
        return redirect('user_profile')
    
    artist_profile = get_object_or_404(ArtistProfile, user_profile=user_profile)
    form = SongUploadForm()
    return render(request, 'users/artist_profile.html', {'user_profile': user_profile, 'artist_profile': artist_profile, 'form': form})


@login_required
def request_artist_status(request):
    user_profile = request.user.profile
    artist_profile, created = ArtistProfile.objects.get_or_create(user_profile=user_profile, defaults={'is_verified': False})
    
    if artist_profile.is_verified:
        messages.info(request, "You are already a verified artist.")
        return redirect('artist_profile')
    elif not created:
        messages.info(request, "Your artist verification is pending approval.")
        return redirect('user_profile')
    
    if request.method == 'POST':
        form = ArtistVerificationForm(request.POST)
        if form.is_valid():
            artist_profile.bio = form.cleaned_data['bio']
            artist_profile.save()
            messages.success(request, "Your artist verification request has been submitted.")
            return redirect('user_profile')
    else:
        form = ArtistVerificationForm()
    
    return render(request, 'users/request_artist_status.html', {'form': form})


@staff_member_required
@csrf_protect
def verify_artist(request, artist_profile_id):
    artist_profile = get_object_or_404(ArtistProfile, id=artist_profile_id)
    
    if request.method == 'POST':
        artist_profile.is_verified = True
        artist_profile.save()
        artist_profile.user_profile.user_type = 'artist'
        artist_profile.user_profile.save()
        
        user = artist_profile.user_profile.user
        for session in Session.objects.all():
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session_data['user_type'] = 'artist'
                session.session_data = Session.objects.encode(session_data)
                session.save()
        
        messages.success(request, f"Artist {user.username} has been verified.")
        return redirect('admin:app_artistprofile_changelist')
    
    return render(request, 'admin/verify_artist_confirmation.html', {'artist_profile': artist_profile})


# CRUD Operations for Songs
@login_required
def upload_song(request):
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'artist':
        messages.error(request, "You must be a verified artist to upload songs.")
        return redirect('home')
    
    artist_profile = request.user.profile.artist_profile
    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.artist = artist_profile
            song.save()
            messages.success(request, "Song uploaded successfully!")
            return redirect('artist_profile')
        messages.error(request, "Error uploading song. Please check the form.")
    else:
        form = SongUploadForm()
    
    return render(request, 'users/artist_profile.html', {'form': form})


def song_list(request):
    songs = Song.objects.filter(is_public=True).select_related('artist')
    return render(request, 'users/song_list.html', {'songs': songs})


def get_songs(request):
    songs = Song.objects.filter(is_public=True).values('id', 'title', 'artist__name', 'audio_file', 'cover_image')
    return JsonResponse(list(songs), safe=False)
