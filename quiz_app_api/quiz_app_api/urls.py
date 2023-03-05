"""Root URL configuration.

The quiz app owns its own paths so that mounting it under a prefix is a
one-line change here rather than an edit spread across the app.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("quiz.urls")),
]
