from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("sessions/", views.sessions_view, name="sessions"),
    path("sessions/<str:conversation_id>/messages/", views.messages_view, name="messages"),
    path(
        "sessions/<str:conversation_id>/",
        views.session_detail_view,
        name="session-detail",
    ),
]
