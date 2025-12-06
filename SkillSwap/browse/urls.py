from django.urls import path
from . import views

app_name = "browse"

urlpatterns = [
    path("profiles/", views.browse_view, name="browse_view"),
    # path("search/", views.search_view, name="search_view"),
]