def user_type(request):
    """
    Add user_type to all template contexts.
    """
    context = {}
    if request.user.is_authenticated:
        # Always fetch fresh data from the database
        from .models import UserProfile
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            context['user_type'] = user_profile.user_type
        except UserProfile.DoesNotExist:
            context['user_type'] = 'user'
    return context