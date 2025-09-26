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

