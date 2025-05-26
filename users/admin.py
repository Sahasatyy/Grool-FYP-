from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, ArtistProfile, Song, Genre, Album, Playlist, PaymentHistory
from django.urls import path
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
import csv
from datetime import timedelta
from .models import SubscriptionPlan, UserSubscription, RevenueRecord

# Custom Admin Site for Grool
from django.contrib.admin import AdminSite

class GroolAdminSite(AdminSite):
    site_header = "Grool"
    site_title = "Grool Admin"
    index_title = "Welcome to Grool Music Admin"

    def each_context(self, request):
        context = super().each_context(request)
        context['site_title'] = "Grool Admin"
        return context

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

# Instantiate custom admin site
grool_admin_site = GroolAdminSite(name='grool_admin')

# UserProfile Admin
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__email')

# ArtistProfile Admin
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
            artist_profile__in=queryset
        ).update(user_type='artist')
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

# SubscriptionPlan Admin
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'duration_days', 'is_active')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name', 'features')

# UserSubscription Admin
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('plan', 'is_active')
    search_fields = ('user__username', 'khalti_idx')
    readonly_fields = ('start_date', 'end_date')

# Custom action for upgrading users to premium
def make_premium(modeladmin, request, queryset):
    for user in queryset:
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.is_premium = True
        profile.premium_expiry = timezone.now() + timedelta(days=30)
        profile.save()
make_premium.short_description = "Upgrade selected users to premium (1 month)"

# Inline for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    actions = [make_premium]

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# RevenueRecord Admin
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

# Registering models to the default admin site
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ArtistProfile, ArtistProfileAdmin)
admin.site.register(Song)
admin.site.register(Genre)
admin.site.register(Playlist)
admin.site.register(Album)

# Customizing default admin site
admin.site.site_header = "Grool - Music Streaming Platform (Admin Dashboard)"
admin.site.site_title = "Grool Admin"
admin.site.index_title = "Welcome to Grool Music Admin"

# Unregister and re-register User with the custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin_site = GroolAdminSite(name='grool_admin')

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('artist', 'amount', 'total_listens', 'requested_at', 'approved_at')
    list_filter = ('approved_at',)
    search_fields = ('artist__user__username',)

from django.utils.timezone import now

from .models import PaymentRequest

@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('artist', 'amount', 'status', 'requested_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('artist__user__username',)
    actions = ['approve_requests', 'reject_requests']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show non-approved requests in the admin queue
        return qs.exclude(status='approved')

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        for payment_request in queryset:
            if payment_request.status != 'approved':
                artist = payment_request.artist
                songs = Song.objects.filter(artist=artist)
                total_listens = sum(song.total_listens for song in songs)

                # Log payment history
                PaymentHistory.objects.create(
                    artist=artist,
                    amount=payment_request.amount,
                    total_listens=total_listens,
                    requested_at=payment_request.requested_at,
                    approved_at=timezone.now()
                )

                # Approve and reset listens
                payment_request.status = 'approved'
                payment_request.save()
                songs.update(total_listens=0)

    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        queryset.update(status='rejected')

grool_admin_site.register(PaymentRequest, PaymentRequestAdmin)