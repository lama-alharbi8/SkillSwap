from django.urls import path
from . import views

app_name = "skills"

urlpatterns = [
    path("add/category/skill", views.cat_skill_add, name="cat_skill_add"),
] 