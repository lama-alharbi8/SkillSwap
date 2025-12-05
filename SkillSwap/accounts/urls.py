from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup_view"),
    path("signin/", views.signin_view, name="signin_view"),
    path("logout/", views.log_out_view, name="log_out_view"),
    path("ajax/categories/<int:pk>/children/", views.category_children, name="category_children"),
    path("ajax/categories/<int:pk>/skills/", views.category_skills, name="category_skills"),
    path("profile/form/", views.profile_form, name="profile_form"),
    path("profile/", views.user_profile, name="user_profile"),

]