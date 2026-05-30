from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/auth/', include('accounts.urls')),

    path('api/households/', include('households.urls')),

    path('api/expenses/', include('expenses.urls')),

    path('api/notifications/', include('notifications.urls')),

    path('api/payments/', include('payments.urls')),
]


# TEMP: Serve uploaded media files on Railway for demo/testing.
# Production lâu dài nên chuyển sang Cloudinary/S3/Firebase Storage.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {
            'document_root': settings.MEDIA_ROOT,
        },
    ),
]