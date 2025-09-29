from django import forms
from .models import Event

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(
        label="Select a CSV file",
        widget=forms.ClearableFileInput(attrs={"id": "csvFileInput", "class": "form-control"})
    )

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "description", "category", "venue", "city", "date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control", "required": True}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "venue": forms.Select(attrs={"class": "form-select"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        venue = cleaned_data.get("venue")
        city = cleaned_data.get("city")

        if venue and not city:
            cleaned_data["city"] = venue.city

        return cleaned_data
