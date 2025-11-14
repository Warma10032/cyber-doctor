from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("refresh/", views.refresh_view, name="refresh"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.me_view, name="me"),
]

