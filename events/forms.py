from django import forms

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(
        label="Select a CSV file",
        widget=forms.ClearableFileInput(attrs={"id": "csvFileInput", "class": "form-control"})
    )