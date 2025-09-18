from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("api/events/", views.events_api, name="events_api"),
    path("signup/", views.signup, name="signup"),
    path("my-events/", views.my_events, name="my_events"),
    path("events/<int:event_id>/delete/", views.delete_event, name="delete_event"),
    path("download-template/", views.download_template, name="download_template"),
]
