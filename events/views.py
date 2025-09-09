import csv
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive
from .forms import UploadCSVForm
from .models import Event, Category, Venue

def index(request):
    events = Event.objects.all().order_by("date")
    return render(request, "events/index.html", {"events": events})

def upload_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file_data = request.FILES["csv_file"].read()

                # Try decoding with UTF-8, fallback to Latin-1
                try:
                    decoded = file_data.decode("utf-8").splitlines()
                except UnicodeDecodeError:
                    decoded = file_data.decode("latin-1").splitlines()

                reader = csv.DictReader(decoded)
                added, skipped, duplicates = 0, 0, 0

                for row in reader:
                    title = row.get("title", "").strip()
                    date_str = row.get("date", "").strip()
                    venue_name = row.get("venue", "").strip()

                    # Basic validation
                    if not title or not date_str or not venue_name:
                        messages.warning(request, f"Skipping row due to missing required fields: {row}")
                        skipped += 1
                        continue

                    parsed_date = parse_datetime(date_str)
                    if not parsed_date:
                        messages.warning(request, f"Skipping row due to invalid date format: {date_str}")
                        skipped += 1
                        continue

                    if is_naive(parsed_date):
                        parsed_date = make_aware(parsed_date)

                    category_name = row.get("category", "Uncategorized").strip()
                    category, _ = Category.objects.get_or_create(name=category_name)

                    venue, _ = Venue.objects.get_or_create(
                        name=venue_name,
                        defaults={
                            "address": row.get("address", "").strip(),
                            "city": row.get("city", "").strip(),
                            "latitude": float(row["latitude"]) if row.get("latitude") else None,
                            "longitude": float(row["longitude"]) if row.get("longitude") else None,
                        }
                    )

                    # Prevent duplicates
                    event, created = Event.objects.get_or_create(
                        title=title,
                        category=category,
                        venue=venue,
                        date=parsed_date,
                        defaults={"description": row.get("description", "").strip()}
                    )

                    if created:
                        added += 1
                    else:
                        messages.info(request, f"Duplicate event skipped: {title} at {venue_name} on {date_str}")
                        duplicates += 1

                messages.success(request, f"Upload complete: {added} added, {duplicates} duplicates, {skipped} skipped.")
                return redirect("index")

            except Exception as e:
                messages.error(request, f"Error processing CSV: {str(e)}")
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
        }
        for e in events
    ]

    return JsonResponse(data, safe=False)
