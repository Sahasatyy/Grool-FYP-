from django.urls import path
from .views import home, RegisterView 
from . import views

urlpatterns = [
    path('', home, name='users-home'),
    path('register/', RegisterView.as_view(), name='users-register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/normal/', views.normal_profile, name='user_profile'),
    path('profile/artist/', views.artist_profile, name='artist_profile'),
    path('become-artist/', views.request_artist_status, name='request_artist_status'),
     path('admin/verify-artist/<int:artist_profile_id>/', views.verify_artist, name='verify_artist'),
    
]