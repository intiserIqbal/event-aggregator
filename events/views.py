#views.py
import csv
import json
from datetime import datetime
from dateutil import parser as date_parser

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils.timezone import make_aware
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .forms import UploadCSVForm, EventForm
from .models import Event, Category, Venue, RSVP

def index(request):
    events = Event.objects.all().order_by("date")

    # 🔎 Apply filters from query params
    category = request.GET.get("category")
    city = request.GET.get("city")
    start_date = request.GET.get("start_date")
    search = request.GET.get("search")

    if category:
        events = events.filter(category__name__iexact=category)
    if city:
        events = events.filter(venue__city__iexact=city)
    if start_date:
        events = events.filter(date__gte=start_date)
    if search:
        events = events.filter(title__icontains=search)

    # RSVP mapping
    user_rsvps = {}
    if request.user.is_authenticated:
        user_rsvps = {r.event_id: r for r in RSVP.objects.filter(user=request.user)}

    events_with_rsvp = [
        {"event": e, "rsvp": user_rsvps.get(e.id)}
        for e in events
    ]

    paginator = Paginator(events_with_rsvp, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "events/index.html", {
        "page_obj": page_obj,
        "selected_category": category or "",
        "selected_city": city or "",
        "selected_search": search or "",
        "selected_start_date": start_date or "",
    })


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

@login_required
@require_POST
def toggle_rsvp(request, event_id):
    try:
        data = json.loads(request.body)
        status = data.get("status")
        if status not in ["going", "interested"]:
            return JsonResponse({"error": "Invalid status"}, status=400)

        existing = RSVP.objects.filter(user=request.user, event_id=event_id).first()

        if existing and existing.status == status:
            # 👈 If user clicks same status again → remove RSVP
            existing.delete()
            return JsonResponse({"success": True, "status": "removed"})
        else:
            rsvp, _ = RSVP.objects.update_or_create(
                user=request.user,
                event_id=event_id,
                defaults={"status": status}
            )
            return JsonResponse({"success": True, "status": rsvp.status})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def my_rsvps(request):
    rsvps = RSVP.objects.filter(user=request.user).select_related("event").order_by("event__date")
    paginator = Paginator(rsvps, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Build dictionary only for events in this page
    user_rsvps = {r.event.id: r.status for r in page_obj}

    return render(request, "events/my_rsvps.html", {
        "page_obj": page_obj,
        "user_rsvps": user_rsvps,
    })

@login_required
def add_event(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.owner = request.user  # ensure ownership
            event.save()
            messages.success(request, "Event created successfully.")
            return redirect("my_events")
    else:
        form = EventForm()
    return render(request, "events/add_event.html", {"form": form})

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id, owner=request.user)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect("my_events")
    else:
        form = EventForm(instance=event)

    return render(request, "events/edit_event.html", {"form": form, "event": event})

def events_api(request):
    events = Event.objects.all().order_by("date")

    # 🔎 Filters from query params
    category = request.GET.get("category")
    city = request.GET.get("city")
    start_date = request.GET.get("start_date")
    search = request.GET.get("search")

    if category:
        events = events.filter(category__name__iexact=category)

    if city:
        # use venue__city for consistency with JSON output
        events = events.filter(venue__city__iexact=city)

    if start_date:
        try:
            # parse YYYY-MM-DD safely
            parsed_date = datetime.strptime(start_date[:10], "%Y-%m-%d")
            events = events.filter(date__gte=make_aware(parsed_date))
        except Exception:
            pass

    if search:
        from django.db.models import Q
        events = events.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(venue__name__icontains=search) |
            Q(category__name__icontains=search)
        )

    # RSVP status
    user = request.user if request.user.is_authenticated else None
    user_rsvps = {}
    if user:
        user_rsvps = {r.event_id: r.status for r in RSVP.objects.filter(user=user)}

    data = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "category": e.category.name if e.category else None,
            "venue": e.venue.name if e.venue else None,
            "city": e.venue.city if e.venue else "",
            "date": e.date.isoformat() if e.date else None,
            "latitude": e.venue.latitude if e.venue else None,
            "longitude": e.venue.longitude if e.venue else None,
            "owner": e.owner.username if e.owner else None,
            "rsvp_status": user_rsvps.get(e.id) if user else None,
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

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    user_rsvp = RSVP.objects.filter(user=request.user, event=event).first()  # direct object

    going_count = RSVP.objects.filter(event=event, status="going").count()
    interested_count = RSVP.objects.filter(event=event, status="interested").count()

    return render(request, "events/event_detail.html", {
        "event": event,
        "user_rsvp": user_rsvp,      # pass directly
        "going_count": going_count,
        "interested_count": interested_count,
    })

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
