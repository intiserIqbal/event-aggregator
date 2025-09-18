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
from dateutil import parser as date_parser
from django.http import HttpResponse

def index(request):
    events = Event.objects.all().order_by("date")
    return render(request, "events/index.html", {"events": events})

def validate_csv(file, user):
    decoded_file = file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded_file)

    required_headers = ["title", "description", "category", "venue", "city", "date"]
    errors, rows, added, duplicates = [], [], 0, 0

    # Check headers
    for h in required_headers:
        if h not in reader.fieldnames:
            errors.append(f"Missing required header: {h}")
            return None, errors, 0, 0

    for i, row in enumerate(reader, start=2):  # start=2 → account for header row
        try:
            title = row["title"].strip()
            if not title:
                errors.append(f"Row {i}: Missing title")
                continue

            date_str = row["date"].strip()
            try:
                date = make_aware(date_parser.parse(date_str, dayfirst=True))
            except Exception:
                errors.append(f"Row {i}: Invalid date format '{date_str}'")
                continue

            category_name = row.get("category", "").strip()
            venue_name = row.get("venue", "").strip()
            city = row.get("city", "").strip()
            lat = row.get("latitude", "").strip()
            lon = row.get("longitude", "").strip()

            latitude = float(lat) if lat else None
            longitude = float(lon) if lon else None

            # ✅ Ensure category exists
            category, _ = Category.objects.get_or_create(name=category_name) if category_name else (None, False)

            # ✅ Ensure venue exists
            venue, created = Venue.objects.get_or_create(
                name=venue_name,
                city=city,
                defaults={"latitude": latitude, "longitude": longitude}
            )

            # ✅ Update coords if venue existed but had no lat/lon
            if not created and (latitude and longitude) and (venue.latitude is None or venue.longitude is None):
                venue.latitude = latitude
                venue.longitude = longitude
                venue.save()

            # ✅ Prevent duplicates
            if Event.objects.filter(title=title, venue=venue, date=date, owner=user).exists():
                duplicates += 1
                continue

            rows.append(Event(
                title=title,
                description=row.get("description", "").strip(),
                category=category,
                venue=venue,
                city=city,
                date=date,
                owner=user,
            ))
            added += 1
        except Exception as e:
            errors.append(f"Row {i}: Unexpected error - {e}")

    return rows, errors, added, duplicates

@login_required
def download_template(request):
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="events_template.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["title", "description", "category", "venue", "city", "date", "latitude", "longitude"])
    writer.writerow([
        "Startup Mixer",
        "Networking event for student entrepreneurs and tech founders",
        "Business",
        "North South University",
        "Dhaka",
        "2025-09-20 16:00",
        "23.8151",
        "90.4256"
    ])
    return response

@login_required
def upload_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["csv_file"]
            rows, errors, added, duplicates = validate_csv(file, request.user)

            if errors:
                for e in errors:
                    messages.error(request, e)

            if rows:
                Event.objects.bulk_create(rows)
                messages.success(request, f"{added} events added successfully.")

            if duplicates:
                messages.warning(request, f"{duplicates} duplicates skipped.")

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
