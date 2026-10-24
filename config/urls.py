"""
Main URL Configuration for Dr. Patt Clinical EMR.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Administration (Hardened with Axes)
    path('admin/', admin.site.urls),

    # Core Public Pages & Landing
    path('', include('core.urls')),

    # Unified Authentication & Session Portal
    path('accounts/', include('accounts.urls')),

    # Doctor Portal (EMR & Patients)
    path('doctor/', include('patients.urls')),

    # 39-Axis Clinical Engine & Reports
    path('clinical/', include('clinical.urls')),

    # Patient Portal & Self-service
    path('patient/', include('portal_patient.urls')),
]

# ในโหมด Development สามารถ serve static/media ได้
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
