from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, ArtistProfile, Song, Genre, Album, Playlist, SubscriptionPlan, UserSubscription
from django.urls import path
from django.db.models import Count

# Register your models here.
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__email')


class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ('artist_name', 'user_profile', 'genre', 'verification_status', 'verification_date')
    list_filter = ('is_verified', 'genre')
    search_fields = ('artist_name', 'user_profile__user__username')
    actions = ['verify_selected_artists']
    
    def verification_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:green">Verified</span>')
        else:
            return format_html('<span style="color:orange">Pending</span>')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:artist_profile_id>/verify/',
                self.admin_site.admin_view(self.verify_artist_view),
                name='verify-artist',
            ),
        ]
        return custom_urls + urls
    
    def verify_artist_view(self, request, artist_profile_id):
        # Import the verify_artist view function here to avoid circular imports
        from .views import verify_artist
        return verify_artist(request, artist_profile_id)
    
    def verify_selected_artists(self, request, queryset):
        for artist_profile in queryset:
            if not artist_profile.is_verified:
                artist_profile.is_verified = True
                artist_profile.save()
                
                user_profile = artist_profile.user_profile
                user_profile.user_type = 'artist'
                user_profile.save()
        
        self.message_user(request, f"{queryset.count()} artists have been verified successfully.")
    verify_selected_artists.short_description = "Verify selected artists"

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ArtistProfile, ArtistProfileAdmin)
admin.site.register(Song)
admin.site.register(Genre)
admin.site.register(Playlist)
admin.site.register(Album)

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'duration_days', 'is_active')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name', 'features')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('plan', 'is_active')
    search_fields = ('user__username', 'khalti_idx')
    readonly_fields = ('start_date', 'end_date')

from .models import RevenueRecord

@admin.register(RevenueRecord)
class RevenueRecordAdmin(admin.ModelAdmin):
    list_display = ('artist', 'song_title', 'amount', 'plays_count', 'calculated_at')
    list_filter = ('artist', 'calculated_at')
    readonly_fields = ('calculated_at',)
    
    def song_title(self, obj):
        return obj.song.title if obj.song else "Deleted Song"
    song_title.short_description = 'Song'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('artist', 'song')