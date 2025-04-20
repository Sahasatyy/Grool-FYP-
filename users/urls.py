from django.urls import path
from .views import home, RegisterView 
from . import views
from .views import upload_song, edit_song, delete_song, toggle_favorite, create_playlist, edit_playlist, delete_playlist, add_song_to_playlist, remove_song_from_playlist, increment_listens
from .views import song_list, get_songs, search, search_suggestions, song_detail, create_album, album_detail, edit_album, delete_album, update_merchandise, update_events
from .views import delete_album_song, subscription_plans, initiate_payment, verify_payment, subscription_success, revenue_details, track_play, revenue_stats, upload_support_qr, remove_support_qr, check_premium
from django.conf import settings
from django.conf.urls.static import static
from users.admin import admin_site

urlpatterns = [
    path('', home, name='users-home'),
    path('admin/', admin_site.urls),
    path('register/', RegisterView.as_view(), name='users-register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/normal/', views.normal_profile, name='user_profile'),
    path('artist/<int:artist_id>/', views.artist_profile, name='artist_profile'),
    path('become-artist/', views.request_artist_status, name='request_artist_status'),
    path('admin/verify-artist/<int:artist_profile_id>/', views.verify_artist, name='verify_artist'),
    path('upload-song/', upload_song, name='upload_song'),
    path('edit-song/<int:song_id>/', edit_song, name='edit_song'),
    path('delete-song/<int:song_id>/', delete_song, name='delete_song'),
    path('songs/', views.song_list, name='song_list'),
    path('get-songs/', get_songs, name='get_songs'),
    path('edit-artist-profile/', views.edit_artist_profile, name='edit_artist_profile'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-email/', views.change_email, name='change_email'),
    path('toggle-favorite/<int:song_id>/', toggle_favorite, name='toggle_favorite'),
    path('create-playlist/', views.create_playlist, name='create_playlist'),
    path('explore/', views.explore, name='explore'),
    path('edit-playlist/<int:playlist_id>/', edit_playlist, name='edit_playlist'),
    path('delete-playlist/<int:playlist_id>/', views.delete_playlist, name='delete_playlist'),
    path('add-song-to-playlist/<int:song_id>/', views.add_song_to_playlist, name='add_song_to_playlist'),
    path('remove-song-from-playlist/<int:playlist_id>/<int:song_id>/', remove_song_from_playlist, name='remove_song_from_playlist'),
    path('playlist/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('song/<int:song_id>/', views.song_detail, name='song_detail'),
    path('search/', search, name='search'),
    path('search-suggestions/', search_suggestions, name='search_suggestions'),
    path('song/<int:song_id>/', song_detail, name='song_details_modal'),
    path('create-album/', views.create_album, name='create_album'),
    path('edit-album/<int:album_id>/', edit_album, name='edit_album'),
    path('delete-album/<int:album_id>/', delete_album, name='delete_album'),
    path('album/<int:album_id>/', views.album_detail, name='album_detail'),
    path('update-merchandise/', update_merchandise, name='update_merchandise'),
    path('update-events/', update_events, name='update_events'),
    path('increment-listens/<int:song_id>/', increment_listens, name='increment_listens'),
    path('album/<int:album_id>/delete-song/<int:song_id>/', delete_album_song, name='delete_album_song'),
    path('subscription/', subscription_plans, name='subscription_plans'),
    path('subscription/initiate/', initiate_payment, name='initiate_payment'),
    path('subscription/verify/', verify_payment, name='verify_payment'),
    path('subscription/success/', subscription_success, name='subscription_success'),
    path('revenue/', views.revenue_details, name='revenue_details'),
    path('track-play/<int:song_id>/', views.track_play, name='track_play'),
    path('revenue-stats/', views.revenue_stats, name='revenue_stats'),
    path('artist/upload_qr/', views.upload_support_qr, name='upload_support_qr'),
    path('artist/remove_qr/', views.remove_support_qr, name='remove_support_qr'),
    path('check-premium/', views.check_premium, name='check_premium'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)