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
from .forms import ProfilePictureForm, EditProfileForm, ChangeEmailForm, PlaylistForm, AlbumForm, SongUploadForm
from .models import ArtistProfile, UserProfile, Song, Favorite, Playlist, Album
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
import requests
from .models import SubscriptionPlan, UserSubscription
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
import random




def home(request):
    songs = Song.objects.filter(is_public=True).select_related('artist')
    user_favorite_ids = []
    if request.user.is_authenticated:
        user_favorite_ids = Favorite.objects.filter(user=request.user).values_list('song_id', flat=True)

    public_playlists = Playlist.objects.filter(is_public=True).select_related('user')
    popular_albums = Album.objects.annotate(num_songs=Count('songs')).order_by('-num_songs')[:5]

    return render(request, 'users/home.html', {
        'songs': songs,
        'user_favorite_ids': user_favorite_ids,
        'public_playlists': public_playlists,
        'popular_albums': popular_albums,
    })

class RegisterView(View):
    form_class = RegisterForm
    template_name = 'users/register.html'
    verification_template = 'users/email_verification.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})


    def send_verification_code(self, request, form):
        email = form.cleaned_data['email']
        code = str(random.randint(100000, 999999))
        
        # Store data in session
        request.session['registration_data'] = {
            'form_data': form.cleaned_data,
            'confirmation_code': code,
            'attempts': 0
        }
        
        # Send email (in production, use Celery for this)
        self.send_verification_email(email, code)
        
        # Redirect to verification page
        return render(request, self.verification_template, {
            'email': email,
            'hide_navbar': True
        })

    def post(self, request, *args, **kwargs):
    # Check if this is a verification attempt
        if 'verification_code' in request.POST:
            return self.handle_verification(request)
        
        # Otherwise process as initial registration
        form = self.form_class(request.POST)
        if form.is_valid():
            return self.send_verification_code(request, form)
        
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})

    def handle_verification(self, request):
        session_data = request.session.get('registration_data', {})
        user_code = request.POST.get('verification_code')
        
        if not session_data:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('users-register')
        
        if session_data.get('confirmation_code') == user_code:
            # Create user from session data (no form validation needed)
            form_data = session_data['form_data']
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=form_data['password1'],
                first_name=form_data['first_name'],
                last_name=form_data['last_name']
            )
            
            del request.session['registration_data']
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
    
        
        # Handle invalid code
        session_data['attempts'] += 1
        request.session['registration_data'] = session_data
        
        if session_data['attempts'] >= 3:
            del request.session['registration_data']
            messages.error(request, 'Too many failed attempts. Please start over.')
            return redirect('users-register')
        
        messages.error(request, 'Invalid verification code. Please try again.')
        return render(request, self.verification_template, {
            'email': session_data['form_data']['email'],
            'hide_navbar': True
        })

    def send_verification_email(self, email, code):
        subject = 'Verify your email address'
        message = f'Your verification code is: {code}'
        from_email = 'noreply@yourdomain.com'  # Update with your email
        recipient_list = [email]
        
        # In production, use Celery task for this
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

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

    # Ensure that you're passing the correct artist_id if needed
    artist_id = user_profile.id if user_profile.user_type == 'artist' else None

    return render(request, 'users/user_profile.html', {
        'user_profile': user_profile,
        'has_artist_request': has_artist_request,
        'artist_id': artist_id  # Pass artist_id if needed
    })


@login_required
def artist_profile(request, artist_id=None):
    # If artist_id is provided, view another artist's profile
    if artist_id:
        artist_profile = get_object_or_404(ArtistProfile, user_profile__user__id=artist_id, is_verified=True)
        user_profile = artist_profile.user_profile
        is_owner = request.user.id == artist_profile.user_profile.user.id
    else:
        # If artist_id is not provided, view the logged-in artist's profile
        user_profile = request.user.profile
        if user_profile.user_type != 'artist':
            messages.error(request, "You don't have artist privileges yet.")
            return redirect('user_profile')
        artist_profile = get_object_or_404(ArtistProfile, user_profile=user_profile)
        is_owner = True  # The logged-in user is the artist

    # Fetch the artist's songs (filter by artist and public status)
    songs = Song.objects.filter(artist=artist_profile, is_public=True)
    albums = artist_profile.albums.all()  # Fetch albums for the artist

    # Handle genre filtering
    selected_genre = request.GET.get('genre')
    if selected_genre:
        songs = songs.filter(genres__name=selected_genre)

    # Fetch unique genres for the filter dropdown
    genres = Song.objects.filter(artist=artist_profile).values_list('genres__name', flat=True).distinct()

    # Pagination (optional, if you want pagination)
    from django.core.paginator import Paginator
    paginator = Paginator(songs, 10)  # Show 10 songs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the form for uploading songs (only if the user is the artist)
    form = SongUploadForm() if is_owner else None

    # Analytics data
    monthly_listeners = artist_profile.monthly_listeners
    total_plays = artist_profile.total_plays
    followers = artist_profile.followers.count()
    total_revenue = artist_profile.total_revenue

    # Context to pass to the template
    context = {
        'user_profile': user_profile,
        'artist_profile': artist_profile,
        'songs': songs,  # Pass all songs (optional, if not using pagination)
        'page_obj': page_obj,  # Pass paginated songs
        'genres': genres,  # Pass genres for the filter dropdown
        'form': form,  # Pass the song upload form (only for the artist)
        'albums': albums,  # Pass albums to the template
        'is_owner': is_owner,  # Pass whether the user is the artist
        'monthly_listeners': monthly_listeners,
        'total_plays': total_plays,
        'followers': followers,
        'total_revenue': total_revenue,
    }

    return render(request, 'users/artist_profile.html', context)

@login_required
def request_artist_status(request):
    # Ensure the user has a profile
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile does not exist.")
        return redirect('home')

    # Get or create the artist profile with all necessary defaults
    artist_profile, created = ArtistProfile.objects.get_or_create(
        user_profile=user_profile,
        defaults={
            'is_verified': False,
            'artist_name': request.user.username,  # Default value
        }
    )

    # Check verification status
    if artist_profile.is_verified:
        messages.info(request, "You are already a verified artist.")
        return redirect('artist_profile')

    # Handle form submission
    if request.method == 'POST':
        form = ArtistVerificationForm(request.POST, request.FILES, instance=artist_profile)
        if form.is_valid():
            # Save the form data to the artist profile
            artist_profile = form.save(commit=False)
            
            # Ensure these fields are set correctly
            artist_profile.user_profile = user_profile
            artist_profile.is_verified = False  # Still needs admin approval
            artist_profile.save()
            
            # Save many-to-many relationships if any
            form.save_m2m()
            
            # Add timestamp for when the request was made
            if not artist_profile.created_at:
                artist_profile.created_at = timezone.now()
                artist_profile.save()
            
            messages.success(request, "Your verification request has been submitted for review.")
            return redirect('user_profile')
    else:
        form = ArtistVerificationForm(instance=artist_profile)

    context = {
        'form': form,
        'existing_request': not created,
    }
    return render(request, 'users/request_artist_status.html', context)


@staff_member_required
@csrf_protect
def verify_artist(request, artist_profile_id):
    artist_profile = get_object_or_404(ArtistProfile, id=artist_profile_id)
    
    if request.method == 'POST':
        # Verify the artist 
        artist_profile.is_verified = True
        artist_profile.save()

        # Update the user profile
        artist_profile.user_profile.user_type = 'artist'
        artist_profile.user_profile.save()

        # Update the user's session (if needed)
        user = artist_profile.user_profile.user
        for session in Session.objects.all():
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session_data['user_type'] = 'artist'
                session.session_data = Session.objects.encode(session_data)
                session.save()

        messages.success(request, f"Artist {user.username} has been verified.")
        return redirect('admin:app_artistprofile_changelist')  # Redirect to the admin panel
    
    return render(request, 'admin/verify_artist_confirmation.html', {'artist_profile': artist_profile})

@login_required
def edit_artist_profile(request):
    user_profile = request.user.profile
    if not hasattr(user_profile, 'artist_profile'):
        messages.error(request, "You are not a verified artist.")
        return redirect('home')

    artist_profile = user_profile.artist_profile

    # Debugging: Print the artist_profile and its associated user ID
    print(f"Artist Profile: {artist_profile}")
    print(f"User ID: {artist_profile.user_profile.user.id}")

    if request.method == 'POST':
        form = ArtistVerificationForm(request.POST, instance=artist_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)
    else:
        form = ArtistVerificationForm(instance=artist_profile)

    return render(request, 'users/edit_artist_profile.html', {'form': form, 'artist_profile': artist_profile})

@login_required
def edit_profile(request):
    user_profile = request.user.profile

    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()

            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()

            messages.success(request, "Your profile has been updated.")
            return redirect('user_profile')
    else:
        form = EditProfileForm(instance=user_profile)

    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def upload_profile_picture(request):
    user_profile = request.user.profile

    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile picture has been updated.")
            
            if user_profile.user_type == 'artist':
                return redirect('artist_profile', artist_id=user_profile.artist_profile.user_profile.user.id)
            else:
                return redirect('user_profile')
    else:
        form = ProfilePictureForm(instance=user_profile)

    return render(request, 'users/upload_profile_picture.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)  # Use PasswordChangeForm
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, "Your password has been changed successfully.")
            return redirect('user_profile')  # Redirect to the user profile page
    else:
        form = PasswordChangeForm(request.user)  # Initialize the form

    return render(request, 'users/change_password.html', {'form': form})

@login_required
def change_email(request):
    if request.method == 'POST':
        form = ChangeEmailForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your email has been updated.")
            return redirect('user_profile')
    else:
        form = ChangeEmailForm(instance=request.user)

    return render(request, 'users/change_email.html', {'form': form})

@login_required
def upload_profile_picture(request):
    user_profile = request.user.profile

    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile picture has been updated.")
            return redirect('user_profile')
    else:
        form = ProfilePictureForm(instance=user_profile)

    return render(request, 'users/upload_profile_picture.html', {'form': form})

@login_required
@csrf_exempt
def toggle_favorite(request, song_id):
    if request.method == "POST":
        song = get_object_or_404(Song, id=song_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, song=song)
        
        if not created:
            # If the favorite already exists, remove it
            favorite.delete()
            return JsonResponse({"is_favorited": False})
        
        # If the favorite was created, return success
        return JsonResponse({"is_favorited": True})
    
    return JsonResponse({"error": "Invalid request"}, status=400)

# CRUD Operations for Songs
@login_required
def upload_song(request):
    try:
        artist_profile = request.user.profile.artist_profile
    except AttributeError:
        messages.error(request, "You must be a verified artist to upload songs.")
        return redirect('home')

    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES, artist=artist_profile)
        if form.is_valid():
            song = form.save(commit=False)
            song.artist = artist_profile
            song.save()
            if song.album:
                song.album.update_total_tracks()
                song.album.update_duration()
            messages.success(request, "Song uploaded successfully!")
            return redirect('artist_profile', artist_id=request.user.id)
    else:
        form = SongUploadForm(artist=artist_profile)

    return render(request, 'users/upload_song.html', {'form': form})


@login_required
def edit_song(request, song_id):
    # Fetch the song to edit
    song = get_object_or_404(Song, id=song_id)

    # Get the artist profile of the user
    try:
        artist_profile = request.user.profile.artist_profile  # Or artist_profile() if it's a method
    except AttributeError:
        messages.error(request, "Artist profile not found.")
        return redirect('home')

    # Ensure the logged-in user is the owner of the song
    if song.artist != artist_profile:
        messages.error(request, "You do not have permission to edit this song.")
        return redirect('artist_profile', artist_id=request.user.id)

    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES, instance=song, artist=artist_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Song updated successfully!")
            return redirect('artist_profile', artist_id=request.user.id)
        else:
            messages.error(request, "Error updating song. Please check the form.")
    else:
        form = SongUploadForm(instance=song, artist=artist_profile)

    return render(request, 'users/edit_song.html', {'form': form, 'song': song})


@login_required
def delete_song(request, song_id):
    # Fetch the song to delete
    song = get_object_or_404(Song, id=song_id)

    # Safely get the artist profile
    try:
        artist_profile = request.user.profile.artist_profile  # or call it if it's a method
    except AttributeError:
        messages.error(request, "Artist profile not found.")
        return redirect('home')

    # Ensure the logged-in user is the owner of the song
    if song.artist != artist_profile:
        messages.error(request, "You do not have permission to delete this song.")
        return redirect('artist_profile', artist_id=request.user.id)

    if request.method == 'POST':
        song.delete()
        messages.success(request, "Song deleted successfully!")
        return redirect('artist_profile', artist_id=request.user.id)

    return render(request, 'users/confirm_delete_song.html', {'song': song})


def song_list(request):
    songs = Song.objects.filter(is_public=True).select_related('artist')
    paginator = Paginator(songs, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'users/song_list.html', {'page_obj': page_obj})


def get_songs(request):
    songs = Song.objects.filter(is_public=True).values('id', 'title', 'artist__name', 'audio_file', 'cover_image')
    return JsonResponse(list(songs), safe=False)


#CRUD Operations for Playlists

from django.contrib import messages
from .models import Playlist, Song  # Make sure these are imported
import json

@login_required
def create_playlist(request):
    # Check authentication
    if not request.user.is_authenticated:
        messages.error(request, 'You need to login to create a playlist.')
        return redirect('login')

    # Initialize variables
    songs = Song.objects.filter(is_public=True)
    messages_json = []
    user_profile = request.user.profile

    if request.method == 'POST':
        form = PlaylistForm(request.POST)

        # Check playlist limit for non-premium users
        if not user_profile.has_active_premium:
            playlist_count = Playlist.objects.filter(user=request.user).count()
            if playlist_count >= 2:
                messages.error(
                    request,
                    'Free users can only create up to 2 playlists. '
                    'Upgrade to premium to create unlimited playlists.'
                )
                # Prepare messages for JSON response
                for message in messages.get_messages(request):
                    messages_json.append({
                        'message': str(message),
                        'tags': message.tags
                    })
                return render(request, 'users/create_playlist.html', {
                    'form': form,
                    'songs': songs,
                    'messages_json': json.dumps(messages_json),
                    'is_premium': user_profile.has_active_premium
                })

        if form.is_valid():
            try:
                # Create the playlist
                playlist = form.save(commit=False)
                playlist.user = request.user
                
                # Set playlist visibility based on user preference
                if user_profile.has_active_premium:
                    playlist.is_public = form.cleaned_data.get('is_public', False)
                else:
                    playlist.is_public = False  # Free users get private playlists by default
                
                playlist.save()

                # Add selected songs
                song_ids = request.POST.getlist('songs')
                added_songs = 0
                missing_songs = []

                for song_id in song_ids:
                    try:
                        song = Song.objects.get(id=song_id, is_public=True)
                        playlist.songs.add(song)
                        added_songs += 1
                    except Song.DoesNotExist:
                        missing_songs.append(song_id)

                # Add messages based on song additions
                if missing_songs:
                    messages.warning(request, f"{len(missing_songs)} songs were not added (invalid or private).")
                if added_songs == 0:
                    messages.warning(request, "No songs were added to your playlist.")
                
                messages.success(request, f'Playlist "{playlist.name}" created successfully!')
                return redirect('playlist_detail', playlist_id=playlist.id)

            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            # Form is invalid - collect specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    else:
        # Initialize form with default values
        initial_data = {}
        if user_profile.has_active_premium:
            initial_data['is_public'] = True  # Default to public for premium users
        form = PlaylistForm(initial=initial_data)

    # Prepare messages for JSON response
    for message in messages.get_messages(request):
        messages_json.append({
            'message': str(message),
            'tags': message.tags
        })

    return render(request, 'users/create_playlist.html', {
        'form': form,
        'songs': songs,
        'messages_json': json.dumps(messages_json),
        'is_premium': user_profile.has_active_premium,
        'current_playlist_count': Playlist.objects.filter(user=request.user).count(),
        'max_free_playlists': 2
    })


@login_required
def edit_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    if request.method == 'POST':
        form = PlaylistForm(request.POST, instance=playlist)
        if form.is_valid():
            form.save()  # Save changes to the playlist
            messages.success(request, 'Playlist updated successfully!')
            return redirect('playlist_detail', playlist_id=playlist.id)
        else:
            messages.error(request, 'Failed to update the playlist. Please check the form.')
    else:
        form = PlaylistForm(instance=playlist)

    return render(request, 'users/edit_playlist.html', {
        'form': form,
        'playlist': playlist,
    })
@login_required
def delete_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    if request.method == "POST":
        playlist.delete()
        return redirect('users-home')
    return render(request, 'users/confirm_delete.html', {'playlist': playlist})

@login_required
def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    songs = playlist.songs.all()
    return render(request, 'users/playlist_detail.html', {'playlist': playlist, 'songs': songs})

def song_detail(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    context = {
        'song': song,
    }
    return render(request, 'users/song_detail_modal.html', context)

@login_required
def add_song_to_playlist(request, song_id):
    if request.method == 'POST':
        playlist_id = request.POST.get('playlist_id')
        song = get_object_or_404(Song, id=song_id)
        playlist = get_object_or_404(Playlist, id=playlist_id)

        # Check if the song is already in the playlist
        if song in playlist.songs.all():
            messages.warning(request, f'"{song.title}" is already in "{playlist.name}".')
        else:
            playlist.songs.add(song)
            messages.success(request, f'"{song.title}" added to "{playlist.name}" successfully!')

        return redirect('explore')

@login_required
def remove_song_from_playlist(request, playlist_id, song_id):
    if request.method == 'POST':
        playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
        song = get_object_or_404(Song, id=song_id)

        # Check if the song is in the playlist
        if song in playlist.songs.all():
            playlist.songs.remove(song)  # Remove only the specified song
            messages.success(request, f'"{song.title}" removed from "{playlist.name}".')
        else:
            messages.warning(request, f'"{song.title}" is not in "{playlist.name}".')

        # Redirect back to the edit playlist page
        return redirect('edit_playlist', playlist_id=playlist.id)
    
def explore(request):
    # Fetch all public songs or other content for the explore page
    songs = Song.objects.filter(is_public=True)
    return render(request, 'users/explore.html', {'songs': songs})

#search system

# views.py
from django.db.models import Q, Count

def search(request):
    query = request.GET.get('q', '')
    results = {
        'songs': [],
        'artists': [],
        'playlists': [],
    }

    if query:
        # Search for songs
        results['songs'] = Song.objects.filter(
            Q(title__icontains=query) | Q(artist__artist_name__icontains=query),
            is_public=True
        ).select_related('artist')

        # Search for artists
        results['artists'] = ArtistProfile.objects.filter(
            Q(artist_name__icontains=query) | Q(user_profile__user__username__icontains=query),
            is_verified=True
        ).select_related('user_profile__user')

        # Search for playlists
        results['playlists'] = Playlist.objects.filter(
            Q(name__icontains=query) | Q(user__username__icontains=query),
            is_public=True
        ).select_related('user')

    # Random recommendations
    random_artists = list(ArtistProfile.objects.filter(is_verified=True).annotate(song_count=Count('songs')).order_by('?')[:3])
    random_songs = list(Song.objects.filter(is_public=True).order_by('?')[:3])
    random_playlists = list(Playlist.objects.filter(is_public=True).annotate(song_count=Count('songs')).order_by('?')[:3])

    return render(request, 'users/search_results.html', {
        'query': query,
        'results': results,
        'random_artists': random_artists,
        'random_songs': random_songs,
        'random_playlists': random_playlists,
    })


def search_suggestions(request):
    query = request.GET.get('q', '')
    suggestions = []

    if query:
        # Add song titles
        songs = Song.objects.filter(title__icontains=query, is_public=True).values_list('title', flat=True)[:5]
        suggestions.extend(songs)

        # Add artist names
        artists = ArtistProfile.objects.filter(artist_name__icontains=query, is_verified=True).values_list('artist_name', flat=True)[:5]
        suggestions.extend(artists)

        # Add playlist names
        playlists = Playlist.objects.filter(name__icontains=query, is_public=True).values_list('name', flat=True)[:5]
        suggestions.extend(playlists)

    return JsonResponse({'suggestions': suggestions})

def song_detail(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    return render(request, 'users/searched_song_details.html', {'song': song})  

#Album CRUD

def create_album(request):
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'artist':
        messages.error(request, "You must be a verified artist to create albums.")
        return redirect('home')

    artist_profile = request.user.profile.artist_profile
    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES)
        if form.is_valid():
            album = form.save(commit=False)
            album.artist = artist_profile
            album.save()
            messages.success(request, "Album created successfully! You can now add songs to it.")
            return redirect('album_detail', album_id=album.id)  # Redirect to album detail page
    else:
        form = AlbumForm()
    return render(request, 'users/create_album.html', {'form': form})

def album_detail(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    songs = album.songs.all()
    song_form = SongUploadForm()
    
    # Get existing songs not in this album
    existing_songs = Song.objects.none()  # Default empty queryset
    if request.user.is_authenticated and hasattr(request.user.profile, 'artist_profile'):
        existing_songs = Song.objects.filter(
            artist=request.user.profile.artist_profile
        ).exclude(
            album=album
        ).select_related('artist')
    
    if request.method == 'POST':
        # Handle adding existing songs
        if 'add_existing_songs' in request.POST:
            song_ids = request.POST.getlist('existing_songs')
            added_count = 0
            for song_id in song_ids:
                try:
                    song = Song.objects.get(id=song_id, artist=request.user.profile.artist_profile)
                    song.album = album
                    song.save()
                    added_count += 1
                except Song.DoesNotExist:
                    continue
            
            if added_count > 0:
                album.update_total_tracks()
                album.update_duration()
                messages.success(request, f"Added {added_count} songs to album!")
            else:
                messages.warning(request, "No songs were added")
            return redirect('album_detail', album_id=album.id)
        
        # Rest of your existing form handling...
    
    return render(request, 'users/album_detail.html', {
        'album': album,
        'songs': songs,
        'song_form': song_form,
        'existing_songs': existing_songs
    })

@login_required
def edit_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    
    # Ensure only the album's artist can edit it
    if request.user.profile.artist_profile != album.artist:
        messages.error(request, "You do not have permission to edit this album.")
        return redirect('artist_profile', artist_id=album.artist.user_profile.user.id)

    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES, instance=album)
        if form.is_valid():
            form.save()
            messages.success(request, "Album updated successfully!")
            return redirect('artist_profile', artist_id=album.artist.user_profile.user.id)  # Pass artist_id
    else:
        form = AlbumForm(instance=album)

    return render(request, 'users/edit_album.html', {'form': form, 'album': album})

@login_required
def delete_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)

    if not hasattr(request.user.profile, 'artist_profile') or request.user.profile.artist_profile != album.artist:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    album.delete()
    messages.success(request, "Album deleted successfully!")
    return redirect('artist_profile', artist_id=album.artist.user_profile.user.id)

from django.core.exceptions import PermissionDenied

@login_required
def update_merchandise(request):
    # Get the artist profile for the currently logged-in user
    artist_profile = get_object_or_404(ArtistProfile, user_profile=request.user.profile)

    if request.method == 'POST':
        artist_profile.merchandise_url = request.POST.get('merchandise_url')
        artist_profile.save()
        messages.success(request, 'Merchandise URL updated successfully!')

    # Corrected redirect using the related user object
    return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)

@login_required
def update_events(request):
    # Get the artist profile for the currently logged-in user
    artist_profile = get_object_or_404(ArtistProfile, user_profile=request.user.profile)

    if request.method == 'POST':
        artist_profile.events_url = request.POST.get('events_url')
        artist_profile.save()
        messages.success(request, 'Events URL updated successfully!')

    # Corrected redirect using the related user object
    return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)

@require_POST
def increment_listens(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    duration = float(request.POST.get('duration', 0))  # Get the duration from the request

    # Increment listens only if the user has listened for at least 5 seconds
    if duration >= 5:
        song.total_listens += 1
        song.save()

    return JsonResponse({'success': True, 'total_listens': song.total_listens})

@require_POST
@login_required
def delete_album_song(request, album_id, song_id):
    try:
        # Get the song and verify it belongs to the requesting artist
        song = Song.objects.get(id=song_id, artist=request.user.profile.artist_profile)
        
        # Remove the song from the album (set album to None)
        song.album = None
        song.save()
        
        # Update album stats
        album = Album.objects.get(id=album_id)
        album.update_total_tracks()
        album.update_duration()
        
        return JsonResponse({
            'success': True,
            'message': 'Song removed from album successfully',
            'album_id': album_id
        })
        
    except Song.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Song not found or not owned by you'}, status=404)
    except Album.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Album not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def subscription_plans(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    context = {
        'plans': plans,
        'current_sub': request.user.subscription if hasattr(request.user, 'subscription') else None
    }
    return render(request, 'payments/subscription_plans.html', context)

def get_return_url(request):
    return_url = request.build_absolute_uri(reverse('verify_payment'))
    if not settings.DEBUG:
        # Handle various cases including load balancers
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            return_url = return_url.replace('http://', 'https://')
        elif not return_url.startswith('https://'):
            return_url = 'https://' + return_url.split('://')[1]
    return return_url

@login_required
def initiate_payment(request):
    if request.method == 'POST':
        try:
            plan_id = request.POST.get('plan_id')
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Use the get_return_url function
            return_url = get_return_url(request)
            
            print(f"RETURN URL: {return_url}")  # Debug print
            
            payload = {
                "return_url": return_url,
                "website_url": request.build_absolute_uri('/'),
                "amount": int(plan.price * 100),
                "purchase_order_id": f"sub_{request.user.id}_{plan.id}",
                "purchase_order_name": f"{plan.name} Subscription",
                "customer_info": {
                    "name": request.user.get_full_name() or request.user.username,
                    "email": request.user.email
                }
            }
            
            headers = {
                "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                settings.KHALTI_INITIATE_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('payment_url'):
                raise ValueError("Missing payment URL in response")
            
            if 'pid' in data:
                request.session['khalti_pid'] = data['pid']
                request.session.modified = True
            
            return JsonResponse({
                'payment_url': data['payment_url'],
                'pid': data.get('pid'),  # Include PID in response
                'success': True
            })
            
        except Exception as e:
            print(f"INITIATION ERROR: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

import logging
logger = logging.getLogger(__name__)

@login_required
def verify_payment(request):
    # Enhanced PID extraction with validation
    pid = None
    potential_pids = [
        request.GET.get('pid'),
        request.POST.get('pid'),
        request.GET.get('transaction_id'),
        request.POST.get('transaction_id'),
        request.session.get('khalti_pid')
    ]
    
    for potential_pid in potential_pids:
        if potential_pid and isinstance(potential_pid, str) and len(potential_pid) > 10:
            pid = potential_pid
            break
    
    if not pid:
        logger.error("Missing PID in verify_payment", extra={
            'user': request.user.id,
            'GET_params': dict(request.GET),
            'POST_params': dict(request.POST),
            'session_data': {'khalti_pid': request.session.get('khalti_pid')}
        })
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'missing_pid',
                'message': 'Payment ID not found in request',
                'available_params': {
                    'GET': dict(request.GET),
                    'POST': dict(request.POST)
                }
            }, status=400)
        
        messages.error(request, "We couldn't verify your payment. Please contact support with your transaction details.")
        return redirect('subscription_plans')
    
    try:
        logger.info(f"Starting payment verification for PID: {pid}", extra={
            'user': request.user.id,
            'pid': pid
        })

        print(f"DEBUG - PID being verified: {pid}") 
        
        # Verify with Khalti with enhanced error handling
        headers = {
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                settings.KHALTI_VERIFY_URL,
                json={"pid": pid},
                headers=headers,
                timeout=15  # Increased timeout
            )
            
            # Log the raw response for debugging
            logger.debug(f"Khalti verification raw response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Khalti API request failed: {str(e)}", exc_info=True)
            raise ValueError("Temporary payment verification issue. Please try again later.")
        
        logger.info("Khalti verification response", extra={
            'user': request.user.id,
            'response_data': data
        })
        
        # Enhanced payment status check
        payment_state = data.get('state', {}).get('name')
        if payment_state != 'Completed':
            logger.warning(f"Payment not completed. State: {payment_state}", extra={
                'user': request.user.id,
                'pid': pid
            })
            raise ValueError(f"Payment status is '{payment_state}'. Please contact support if this is incorrect.")
        
        # Extract purchase details with better error handling
        purchase_order_id = data.get('product_identity') or data.get('purchase_order_id')
        if not purchase_order_id:
            logger.error("Missing purchase order ID in Khalti response", extra={
                'user': request.user.id,
                'response_data': data
            })
            raise ValueError("Could not identify your subscription plan.")
        
        try:
            plan_id = purchase_order_id.split('_')[-1]
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except (ValueError, IndexError, SubscriptionPlan.DoesNotExist) as e:
            logger.error(f"Invalid plan ID in purchase order: {purchase_order_id}", exc_info=True)
            raise ValueError("Invalid subscription plan reference.")
        
        # Create/update subscription with transaction safety
        try:
            subscription, created = UserSubscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'plan': plan,
                    'is_active': True,
                    'khalti_idx': data.get('idx', ''),
                    'payment_verified': True,
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=plan.duration_days),
                    'last_payment_data': data  # Store full response for reference
                }
            )
            
            logger.info(f"{'Created' if created else 'Updated'} subscription", extra={
                'user': request.user.id,
                'subscription_id': subscription.id,
                'plan_id': plan.id
            })
            
        except Exception as e:
            logger.error("Failed to create/update subscription", exc_info=True)
            raise ValueError("Failed to activate your subscription. Please contact support.")
        
        # Clear session data
        if 'khalti_pid' in request.session:
            del request.session['khalti_pid']
            request.session.modified = True
        
        # Send success notification
        messages.success(request, "Payment verified successfully! Your subscription is now active.")
        return redirect('subscription_success')
        
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}", exc_info=True)
        messages.error(request, f"Payment verification failed: {str(e)}")
        return redirect('subscription_plans')

@login_required
def subscription_success(request):
    # Additional security check
    if not hasattr(request.user, 'subscription') or not request.user.subscription.payment_verified:
        messages.warning(request, "No valid subscription found")
        return redirect('subscription_plans')
    
    # Add context data for the template
    context = {
        'subscription': request.user.subscription,
        'plan': request.user.subscription.plan,
        'expiry_date': request.user.subscription.end_date.strftime("%B %d, %Y")
    }
    
    return render(request, 'users/subscription_success.html', context)

@login_required
def check_premium(request):
    return JsonResponse({
        'is_premium': request.user.profile.has_active_premium
    })

from django.db.models import F, ExpressionWrapper, DecimalField

@login_required
def revenue_details(request):
    if not hasattr(request.user.profile, 'artist_profile'):
        return HttpResponseForbidden("Only artists can view revenue details")
    
    artist_profile = request.user.profile.artist_profile
    
    # Calculate real-time stats
    songs = Song.objects.filter(artist=artist_profile).annotate(
        revenue_per_1k=ExpressionWrapper(
            F('qualified_plays') / 1000 * 100,
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
        play_time_hours=ExpressionWrapper(
            F('play_duration') / timedelta(hours=1),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).order_by('-revenue')

    # Calculate totals
    total_revenue = sum(song.revenue for song in songs)
    total_plays = sum(song.total_listens for song in songs)
    total_qualified = sum(song.qualified_plays for song in songs)
    total_play_time = sum((song.play_duration for song in songs), timedelta())

    context = {
        'songs': songs,
        'total_revenue': total_revenue,
        'total_plays': total_plays,
        'total_qualified': total_qualified,
        'total_play_time': total_play_time,
        'artist_profile': artist_profile
    }
    return render(request, 'users/revenue_details.html', context)

from .models import Song, RevenueRecord, PlayHistory

@require_POST
@csrf_exempt
def track_play(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    duration = int(request.POST.get('duration', 0))
    
    # Update song stats
    if duration >= 60:
        song.play_duration += timedelta(seconds=duration)
        song.qualified_plays += 1
        song.total_listens += 1
        
        new_revenue = (song.qualified_plays // 1000) * 100
        if new_revenue > song.revenue:
            RevenueRecord.objects.create(
                artist=song.artist,
                song=song,
                amount=new_revenue - song.revenue,
                plays_count=song.qualified_plays
            )
            song.revenue = new_revenue
        
        qualified = True
    else:
        song.total_listens += 1
        qualified = False
    
    song.save()
    
    # Record play history
    PlayHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        song=song,
        play_duration=timedelta(seconds=duration),
        qualified=qualified
    )
    
    # Return updated stats
    artist_profile = song.artist
    songs = Song.objects.filter(artist=artist_profile).values(
        'id', 'total_listens', 'qualified_plays', 'play_duration', 'revenue'
    )
    
    return JsonResponse({
        'status': 'success',
        'qualified': qualified,
        'song_id': song.id,
        'updated_stats': {
            'total_listens': song.total_listens,
            'qualified_plays': song.qualified_plays,
            'play_duration': str(song.play_duration),
            'revenue': song.revenue
        }
    })

@login_required
def revenue_stats(request):
    if not hasattr(request.user.profile, 'artist_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    artist_profile = request.user.profile.artist_profile
    
    songs = Song.objects.filter(artist=artist_profile).values(
        'id', 'title', 'total_listens', 'qualified_plays', 'play_duration', 'revenue'
    )
    
    # Calculate totals
    total_revenue = sum(song['revenue'] for song in songs)
    total_plays = sum(song['total_listens'] for song in songs)
    total_qualified = sum(song['qualified_plays'] for song in songs)
    total_play_time = sum(
        song['play_duration'].total_seconds() if isinstance(song['play_duration'], timedelta) else 0 
        for song in songs
    )
    
    # Convert play_time to readable format
    total_play_time = str(timedelta(seconds=total_play_time))
    
    return JsonResponse({
        'songs': list(songs),
        'total_revenue': total_revenue,
        'total_plays': total_plays,
        'total_qualified': total_qualified,
        'total_play_time': total_play_time
    })

from .forms import SupportQRForm
import os

@login_required
def upload_support_qr(request):
    artist_profile = get_object_or_404(ArtistProfile, user_profile__user=request.user)
    
    if request.method == 'POST':
        form = SupportQRForm(request.POST, request.FILES, instance=artist_profile)
        if form.is_valid():
            try:
                # Delete old QR code if exists
                if artist_profile.support_qr_code:
                    artist_profile.support_qr_code.delete()
                
                # Save the new QR code
                artist_profile = form.save()
                
                # Verify the file was saved
                if artist_profile.support_qr_code:
                    messages.success(request, 'QR code uploaded successfully!')
                    return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)
                else:
                    messages.error(request, 'Failed to save QR code')
            except Exception as e:
                messages.error(request, f'Error uploading QR code: {str(e)}')
        else:
            messages.error(request, 'Invalid form data')
    
    return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)


@login_required
def remove_support_qr(request):
    artist_profile = get_object_or_404(ArtistProfile, user_profile__user=request.user)
    
    if artist_profile.support_qr_code:
        artist_profile.support_qr_code.delete()
        artist_profile.support_qr_code = None
        artist_profile.save()
        messages.success(request, 'QR code removed!')
    
    return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)