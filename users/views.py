from django.contrib import messages
from django.views import View
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from django.shortcuts import render, redirect
from .models import UserProfile, ArtistProfile
from .forms import ArtistVerificationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse


def home(request):
    return render(request, 'users/home.html')

class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        # Redirect to home if user is already authenticated
        if request.user.is_authenticated:
            return redirect(to='home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})  # Hide navbar

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created successfully for {user.username}! You can now log in.')
            return redirect(to='login')
        return render(request, self.template_name, {'form': form, 'hide_navbar': True})  # Hide navbar

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
            self.request.session.modified = True
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_navbar'] = True  # Hide navbar
        return context



@login_required
def profile_view(request):
    user_profile = request.user.profile
    
    # Redirect to appropriate profile page based on user type
    if user_profile.user_type == 'artist':
        return redirect('artist_profile')
    else:
        return redirect('user_profile')

@login_required
def normal_profile(request):
    user_profile = request.user.profile
    
    # Check if there's a pending artist request
    has_artist_request = ArtistProfile.objects.filter(
        user_profile=user_profile, 
        is_verified=False
    ).exists()
    
    context = {
        'user_profile': user_profile,
        'has_artist_request': has_artist_request,
    }
    return render(request, 'users/user_profile.html', context)

@login_required
def artist_profile(request):
    user_profile = request.user.profile
    
    # Ensure the user is actually an artist type
    if user_profile.user_type != 'artist':
        messages.error(request, "You don't have artist privileges yet.")
        return redirect('user_profile')
        
    try:
        artist_profile = user_profile.artist_profile
    except ArtistProfile.DoesNotExist:
        # Handle the case where someone with 'artist' type doesn't have an artist profile yet
        return redirect('create_artist_profile')
    
    context = {
        'user_profile': user_profile,
        'artist_profile': artist_profile,
    }
    return render(request, 'users/artist_profile.html', context)

@login_required
def request_artist_status(request):
    # Check if the user already has an artist profile or pending request
    user_profile = request.user.profile
    
    try:
        # If artist profile exists, check its verification status
        artist_profile = ArtistProfile.objects.get(user_profile=user_profile)
        
        if artist_profile.is_verified and user_profile.user_type == 'artist':
            messages.info(request, "You are already a verified artist.")
            return redirect('artist_profile')
        elif not artist_profile.is_verified:
            messages.info(request, "Your artist verification is pending approval.")
            return redirect('user_profile')
    except ArtistProfile.DoesNotExist:
        # Continue with the form submission process
        pass
    
    if request.method == 'POST':
        form = ArtistVerificationForm(request.POST)
        if form.is_valid():
            # Create artist profile but don't change user type yet
            artist_profile = form.save(commit=False)
            artist_profile.user_profile = user_profile
            artist_profile.is_verified = False  # Explicitly set to false
            artist_profile.save()
            
            messages.success(request, "Your artist verification request has been submitted and is pending approval.")
            return redirect('user_profile')
    else:
        form = ArtistVerificationForm()
    
    return render(request, 'users/request_artist_status.html', {'form': form})

# Add a new admin action to verify artists
@staff_member_required
@csrf_protect
def verify_artist(request, artist_profile_id):
    if request.method == 'POST':
        try:
            artist_profile = ArtistProfile.objects.get(id=artist_profile_id)
            artist_profile.is_verified = True
            artist_profile.save()
            
            # Update the user_type to 'artist'
            user_profile = artist_profile.user_profile
            user_profile.user_type = 'artist'
            user_profile.save()
            
            # Add this: Force session update if the user is currently logged in
            from django.contrib.sessions.models import Session
            from django.contrib.auth.models import User
            user = user_profile.user
            
            # Find all sessions for this user
            for session in Session.objects.all():
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(user.id):
                    # Update user type in session
                    session_data['user_type'] = 'artist'
                    session.session_data = Session.objects.encode(session_data)
                    session.save()
            
            messages.success(request, f"Artist {user_profile.user.username} has been verified.")
        except ArtistProfile.DoesNotExist:
            messages.error(request, "Artist profile not found.")
        
        return redirect('admin:app_artistprofile_changelist')
    
    # For GET requests, show a confirmation page with a form
    artist_profile = get_object_or_404(ArtistProfile, id=artist_profile_id)
    return render(request, 'admin/verify_artist_confirmation.html', {
        'artist_profile': artist_profile,
    })