from django.urls import path
from . import views

app_name = "skills"

urlpatterns = [
    path("add/", views.add_skill_view, name="add_skill_view"),
] 