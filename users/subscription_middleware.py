from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect

class SubscriptionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip for certain paths
        if request.path.startswith(('/admin/', '/static/', '/media/', '/accounts/')):
            return None
        
        # Check for ad-free paths
        if request.path.startswith('/player/') or request.path.startswith('/premium/'):
            if not request.user.is_authenticated:
                messages.warning(request, "Please login to access premium content")
                return redirect(reverse('login') + f'?next={request.path}')
            
            if not hasattr(request.user, 'subscription') or not request.user.subscription.is_valid:
                messages.warning(request, "Premium subscription required")
                return redirect('subscription_plans')
        
        return None