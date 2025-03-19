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
        return redirect('home')  # Redirect to a safe page

    # Get or create the artist profile
    artist_profile, created = ArtistProfile.objects.get_or_create(
        user_profile=user_profile,
        defaults={'is_verified': False}
    )

    # Check if the artist is already verified
    if artist_profile.is_verified:
        messages.info(request, "You are already a verified artist.")
        return redirect('artist_profile')  # Redirect to the artist profile page

    # Check if the artist profile already exists (pending verification)
    elif not created:
        messages.info(request, "Your artist verification is pending approval.")
        return redirect('user_profile')  # Redirect to the user profile page

    # Handle form submission
    if request.method == 'POST':
        form = ArtistVerificationForm(request.POST, request.FILES, instance=artist_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your artist verification request has been submitted.")
            return redirect('user_profile')  # Redirect to the user profile page
    else:
        form = ArtistVerificationForm(instance=artist_profile)

    return render(request, 'users/request_artist_status.html', {'form': form})


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
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'artist':
        messages.error(request, "You must be a verified artist to upload songs.")
        return redirect('home')

    artist_profile = request.user.profile.artist_profile
    if not hasattr(artist_profile, 'user_profile'):
        messages.error(request, "Artist profile is incomplete.")
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
            # Fallback to home if artist_id is missing
            if hasattr(artist_profile.user_profile.user, 'id'):
                return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)
            else:
                messages.error(request, "Invalid artist profile.")
                return redirect('home')
    else:
        form = SongUploadForm(artist=artist_profile)
    return render(request, 'users/upload_song.html', {'form': form})

@login_required
def edit_song(request, song_id):
    # Fetch the song to edit
    song = get_object_or_404(Song, id=song_id)

    # Ensure the logged-in user is the owner of the song
    if song.artist != request.user.profile.artist_profile:
        messages.error(request, "You do not have permission to edit this song.")
        return redirect('artist_profile')

    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES, instance=song)
        if form.is_valid():
            form.save()
            messages.success(request, "Song updated successfully!")
            return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)
        else:
            messages.error(request, "Error updating song. Please check the form.")
    else:
        form = SongUploadForm(instance=song)

    return render(request, 'users/edit_song.html', {'form': form, 'song': song})

@login_required
def delete_song(request, song_id):
    # Fetch the song to delete
    song = get_object_or_404(Song, id=song_id)

    # Ensure the logged-in user is the owner of the song
    if song.artist != request.user.profile.artist_profile:
        messages.error(request, "You do not have permission to delete this song.")
        return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)

    if request.method == 'POST':
        song.delete()
        messages.success(request, "Song deleted successfully!")
        return redirect('artist_profile', artist_id=artist_profile.user_profile.user.id)

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

def create_playlist(request):
    if request.method == 'POST':
        form = PlaylistForm(request.POST)
        if form.is_valid():
            # Create the playlist
            playlist = form.save(commit=False)
            playlist.user = request.user  # Set the playlist owner
            playlist.save()

            # Add selected songs to the playlist
            song_ids = request.POST.getlist('songs')  # Get selected song IDs
            for song_id in song_ids:
                try:
                    song = Song.objects.get(id=song_id, is_public=True)  # Ensure the song is public
                    playlist.songs.add(song)
                except Song.DoesNotExist:
                    messages.warning(request, f'Song with ID {song_id} does not exist or is not public.')

            messages.success(request, 'Playlist created successfully!')
            return redirect('playlist_detail', playlist_id=playlist.id)
        else:
            messages.error(request, 'Failed to create the playlist. Please check the form.')
    else:
        form = PlaylistForm()

    # Fetch all public songs for the form
    songs = Song.objects.filter(is_public=True)
    return render(request, 'users/create_playlist.html', {
        'form': form,
        'songs': songs,
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

    if request.method == 'POST':
        song_form = SongUploadForm(request.POST, request.FILES, artist=album.artist)
        if song_form.is_valid():
            song = song_form.save(commit=False)
            song.artist = album.artist
            song.album = album
            song.save()
            album.update_total_tracks()  # Update total tracks in the album
            album.update_duration()  # Update total duration of the album
            messages.success(request, "Song added to the album successfully!")
            return redirect('album_detail', album_id=album.id)
    else:
        song_form = SongUploadForm(artist=album.artist)

    return render(request, 'users/album_detail.html', {
        'album': album,
        'songs': songs,
        'song_form': song_form,  # Pass the song upload form to the template
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
    
    # Ensure only the album's artist can delete it
    if request.user.profile.artist_profile != album.artist:
        messages.error(request, "You do not have permission to delete this album.")
        return redirect('artist_profile', artist_id=album.artist.user_profile.user.id)

    album.delete()
    messages.success(request, "Album deleted successfully!")
    return redirect('artist_profile', artist_id=album.artist.user_profile.user.id)

@login_required
def follow_artist(request, artist_id):
    artist_profile = get_object_or_404(ArtistProfile, id=artist_id)
    user_profile = request.user.profile

    if artist_profile in user_profile.followed_artists.all():
        user_profile.followed_artists.remove(artist_profile)
    else:
        user_profile.followed_artists.add(artist_profile)

    return redirect('artist_profile', artist_id=artist_id)


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