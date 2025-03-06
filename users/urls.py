from django.urls import path
from .views import home, RegisterView 
from . import views
from .views import upload_song
from .views import song_list, get_songs
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='users-home'),
    path('register/', RegisterView.as_view(), name='users-register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/normal/', views.normal_profile, name='user_profile'),
    path('profile/artist/', views.artist_profile, name='artist_profile'),
    path('become-artist/', views.request_artist_status, name='request_artist_status'),
    path('admin/verify-artist/<int:artist_profile_id>/', views.verify_artist, name='verify_artist'),
    path('upload-song/', upload_song, name='upload_song'),
    path('songs/', views.song_list, name='song_list'),
    path('get-songs/', get_songs, name='get_songs'),
    path('edit-artist-profile/', views.edit_artist_profile, name='edit_artist_profile'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-email/', views.change_email, name='change_email'),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)