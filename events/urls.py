# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("my-events/", views.my_events, name="my_events"),
    path("my-rsvps/", views.my_rsvps, name="my_rsvps"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("download-template/", views.download_template, name="download_template"),
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("events/<int:event_id>/rsvp/", views.toggle_rsvp, name="toggle_rsvp"),
    path("events/<int:event_id>/delete/", views.delete_event, name="delete_event"),
    path("api/events/", views.events_api, name="events_api"),
    path("signup/", views.signup, name="signup"),
    path("events/<int:event_id>/edit/", views.edit_event, name="edit_event"),
    path("events/add/", views.add_event, name="add_event"),
]
