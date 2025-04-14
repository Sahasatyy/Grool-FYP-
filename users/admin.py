from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, ArtistProfile, Song, Genre, Album, Playlist, SubscriptionPlan, UserSubscription
from django.urls import path
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist

import csv

from .models import ArtistProfile, UserProfile


# Register your models here.
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__email')


class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = (
        'artist_name',
        'user_profile',
        'get_genre',
        'verification_status',
        'get_created_at',
        'verification_date',
        'is_verified'
    )
    list_filter = (
        'is_verified',
        'genre',
    )
    try:
        ArtistProfile._meta.get_field('created_at')
        list_filter += (('created_at', admin.DateFieldListFilter),)
        date_hierarchy = 'created_at'
    except FieldDoesNotExist:
        pass
    
    readonly_fields = (
        'get_created_at',
        'verification_date',
        'user_profile',
        'verification_status'
    )
    search_fields = (
        'artist_name',
        'user_profile__user__username',
        'user_profile__user__email'
    )
    actions = [
        'verify_selected_artists',
        'reject_selected_artists',
        'export_as_csv'
    ]
    date_hierarchy = 'created_at'
    list_select_related = ('user_profile', 'user_profile__user')

    fieldsets = (
        ('Artist Information', {
            'fields': (
                'user_profile',
                'artist_name',
                'profile_picture',
                'genre',
                'bio',
                'description_about_yourself',
                'social_links'
            )
        }),
        ('Verification Status', {
            'fields': (
                'is_verified',
                'verification_status',
                'created_at',
                'verification_date'
            )
        }),
    )
    def get_created_at(self, obj):
        if hasattr(obj, 'created_at'):
            return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "-"
        return "Not available"
    get_created_at.short_description = 'Created At'

    def get_genre(self, obj):
        """Display the genre for a single CharField"""
        return obj.genre if obj.genre else "-"
    get_genre.short_description = 'Genre'

    def verification_status(self, obj):
        if obj.is_verified:
            return format_html(
                '<span class="verified-badge" style="color:green; font-weight:bold">✓ Verified</span>'
            )
        return format_html(
            '<span class="pending-badge" style="color:orange; font-weight:bold">⌛ Pending</span>'
        )
    verification_status.short_description = 'Status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:artist_profile_id>/verify/',
                self.admin_site.admin_view(self.verify_artist_view),
                name='verify-artist',
            ),
            path(
                '<int:artist_profile_id>/preview/',
                self.admin_site.admin_view(self.preview_artist_view),
                name='preview-artist',
            ),
        ]
        return custom_urls + urls

    def verify_artist_view(self, request, artist_profile_id):
        from .views import verify_artist
        return verify_artist(request, artist_profile_id)

    def preview_artist_view(self, request, artist_profile_id):
        artist = get_object_or_404(ArtistProfile, id=artist_profile_id)
        return render(request, 'admin/artist_preview.html', {'artist': artist})

    def verify_selected_artists(self, request, queryset):
        updated = queryset.filter(is_verified=False).update(
            is_verified=True,
            verification_date=timezone.now()
        )
        UserProfile.objects.filter(
            artistprofile__in=queryset
        ).update(user_type='artist')
        
        # # Send verification emails
        # for artist in queryset:
        #     send_verification_email(artist)
        
        self.message_user(
            request,
            f"Successfully verified {updated} artist(s). Notification emails sent."
        )
    verify_selected_artists.short_description = "Verify selected artists"

    def reject_selected_artists(self, request, queryset):
        updated = queryset.filter(is_verified=False).update(
            verification_date=None
        )
        self.message_user(
            request,
            f"Marked {updated} pending request(s) as rejected."
        )
    reject_selected_artists.short_description = "Reject selected requests"

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        
        return response
    export_as_csv.short_description = "Export Selected"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_verified=False)
        return qs

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