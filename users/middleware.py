from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class ArtistRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before the view is called
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # This is called just before Django calls the view
        if request.user.is_authenticated:
            # Check if we're on the user profile page and the user is an artist
            if request.path == reverse('user_profile'):
                # Get fresh user profile data
                user_profile = request.user.profile
                
                if user_profile.user_type == 'artist':
                    messages.info(request, "You've been redirected to your artist dashboard.")
                    return redirect('artist_profile', artist_id=user_profile.id)
        return None