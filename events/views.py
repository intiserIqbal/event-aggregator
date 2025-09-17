import csv
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import make_aware
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .forms import UploadCSVForm
from .models import Event, Category, Venue


def index(request):
    events = Event.objects.all().order_by("date")
    return render(request, "events/index.html", {"events": events})

@login_required
def upload_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["csv_file"]

            if not file.name.endswith(".csv"):
                messages.error(request, "Invalid file type. Please upload a .csv file.")
                return redirect("upload_csv")

            try:
                decoded_file = file.read().decode("utf-8").splitlines()
            except UnicodeDecodeError:
                file.seek(0)
                decoded_file = file.read().decode("latin-1").splitlines()

            reader = csv.DictReader(decoded_file)
            added, skipped_invalid, skipped_duplicates = 0, 0, 0

            for row in reader:
                try:
                    title = row["title"].strip()
                    description = row.get("description", "").strip()
                    category_name = row.get("category", "").strip()
                    venue_name = row.get("venue", "").strip()
                    city = row.get("city", "").strip()
                    date_str = row["date"].strip()

                    # ✅ Try to parse date
                    try:
                        date = make_aware(datetime.fromisoformat(date_str))
                    except Exception:
                        skipped_invalid += 1
                        continue

                    # ✅ Parse lat/lng if present
                    lat = row.get("latitude", "").strip()
                    lon = row.get("longitude", "").strip()
                    latitude = float(lat) if lat else None
                    longitude = float(lon) if lon else None

                    # ✅ Category & Venue
                    category, _ = Category.objects.get_or_create(name=category_name) if category_name else (None, False)
                    venue, _ = Venue.objects.get_or_create(
                        name=venue_name, city=city,
                        defaults={"latitude": latitude, "longitude": longitude}
                    )

                    # ✅ If venue already exists but missing coords, update them
                    if venue and (latitude and longitude) and (venue.latitude is None or venue.longitude is None):
                        venue.latitude = latitude
                        venue.longitude = longitude
                        venue.save()

                    # ✅ Avoid duplicate events for same user
                    if Event.objects.filter(title=title, venue=venue, date=date, owner=request.user).exists():
                        skipped_duplicates += 1
                        continue

                    Event.objects.create(
                        title=title,
                        description=description,
                        category=category,
                        venue=venue,
                        city=city,
                        date=date,
                        owner=request.user,
                    )
                    added += 1

                except KeyError as e:
                    messages.error(request, f"Missing column: {e}. Make sure CSV has the correct headers.")
                    return redirect("upload_csv")

            if added:
                messages.success(request, f"{added} events added successfully.")
            if skipped_duplicates:
                messages.warning(request, f"{skipped_duplicates} duplicate events skipped.")
            if skipped_invalid:
                messages.warning(request, f"{skipped_invalid} invalid rows skipped.")

            return redirect("upload_csv")

    else:
        form = UploadCSVForm()

    return render(request, "events/upload_csv.html", {"form": form})

def events_api(request):
    events = Event.objects.all()

    category = request.GET.get("category")
    venue = request.GET.get("venue")
    city = request.GET.get("city")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if category:
        events = events.filter(category__name__iexact=category)
    if venue:
        events = events.filter(venue__name__icontains=venue)
    if city:
        events = events.filter(venue__city__icontains=city)
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            events = events.filter(date__gte=start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            events = events.filter(date__lte=end)
        except ValueError:
            pass

    data = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "category": e.category.name if e.category else None,
            "venue": e.venue.name if e.venue else None,
            "address": e.venue.address if e.venue else "",
            "city": e.venue.city if e.venue else "",
            "date": e.date.isoformat() if e.date else None,
            "latitude": e.venue.latitude if e.venue else None,
            "longitude": e.venue.longitude if e.venue else None,
            "owner": e.owner.username if hasattr(e, "owner") and e.owner else None,
        }
        for e in events
    ]

    return JsonResponse(data, safe=False)


# My Events with pagination
@login_required
def my_events(request):
    events_qs = Event.objects.filter(owner=request.user).order_by("date")
    paginator = Paginator(events_qs, 10)  # 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "events/my_events.html", {"page_obj": page_obj})


# Delete event (owner only)
@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id, owner=request.user)
    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted.")
        return redirect("my_events")
    # fallback confirmation page if accessed by GET
    return render(request, "events/confirm_delete.html", {"event": event})


# Signup view
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})
