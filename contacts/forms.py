from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            "name",
            "email",
            "message",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control"}),
        }
        labels = {
            "name": "Nome",
            "email": "Email",
            "message": "Messaggio",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div(
                    "name",
                    "email",
                    "message",
                ),
            ),
            Div(
                Submit(
                    "submit",
                    "Invia Messaggio",
                    css_class="w-full md:w-auto btn btn-sm btn-primary mt-2",
                ),
                css_class="md:text-right",
            ),
        )
