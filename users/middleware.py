from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


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
    
class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip for certain paths
        exempt_paths = ['/admin/', '/static/', '/media/', '/accounts/', '/subscription/']
        if any(request.path.startswith(path) for path in exempt_paths):
            return None
        
        # Check for premium content paths
        premium_paths = ['/player/', '/premium/']
        if any(request.path.startswith(path) for path in premium_paths):
            if not request.user.is_authenticated:
                messages.warning(request, "Please login to access premium content")
                return redirect(reverse('login') + f'?next={request.path}')
            
            if not hasattr(request.user, 'subscription') or not request.user.subscription.is_valid:
                messages.warning(request, "Premium subscription required")
                return redirect('subscription_plans')
        
        return None

class KhaltiPIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check for PID in sessionStorage fallback
        if 'khalti_pid' in request.GET:
            request.session['khalti_pid'] = request.GET['khalti_pid']
        return self.get_response(request)