# models.py
from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateTimeField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")

    def __str__(self):
        return f"{self.title} ({self.date.strftime('%Y-%m-%d')})"

class RSVP(models.Model):
    STATUS_CHOICES = [
        ("interested", "Interested"),
        ("going", "Going"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rsvps")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ("user", "event")  # prevent duplicate RSVPs

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"