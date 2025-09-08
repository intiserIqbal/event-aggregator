import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UploadCSVForm
from .models import Event, Category, Venue
from django.utils.dateparse import parse_datetime

def index(request):
    events = Event.objects.all().order_by("date")
    return render(request, "events/index.html", {"events": events})

def upload_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Try decoding with UTF-8, fallback to Latin-1
                file_data = request.FILES["csv_file"].read()
                try:
                    decoded = file_data.decode("utf-8").splitlines()
                except UnicodeDecodeError:
                    decoded = file_data.decode("latin-1").splitlines()

                reader = csv.DictReader(decoded)

                for row in reader:
                    category, _ = Category.objects.get_or_create(name=row["category"])

                    venue, _ = Venue.objects.get_or_create(
                        name=row["venue"],
                        defaults={
                            "address": row.get("address", ""),
                            "city": row.get("city", ""),
                            "latitude": float(row["latitude"]) if row.get("latitude") else None,
                            "longitude": float(row["longitude"]) if row.get("longitude") else None,
                        }
                    )

                    Event.objects.create(
                        title=row["title"],
                        description=row.get("description", ""),
                        category=category,
                        venue=venue,
                        date=parse_datetime(row["date"])
                    )

                messages.success(request, "CSV uploaded successfully!")
                return redirect("index")

            except Exception as e:
                messages.error(request, f"Error processing CSV: {str(e)}")
                return redirect("upload_csv")

    else:
        form = UploadCSVForm()

    return render(request, "events/upload_csv.html", {"form": form})
