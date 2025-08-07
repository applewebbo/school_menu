from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout
from django import forms

from contacts.models import MenuReport


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Nome")
    email = forms.EmailField(label="Indirizzo email")
    message = forms.CharField(widget=forms.Textarea, label="Messaggio")
    widgets = {
        "name": forms.TextInput(attrs={"class": "input w-full"}),
        "email": forms.EmailInput(attrs={"class": "input w-full"}),
        "message": forms.Textarea(attrs={"class": "textarea w-full"}),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Field("name", css_class="input w-full"),
                    Field("email", css_class="input w-full"),
                    Field("message", css_class="h-36 textarea w-full"),
                ),
            ),
        )


class MenuReportForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label="Nome")
    message = forms.CharField(widget=forms.Textarea, label="Messaggio")
    get_notified = forms.BooleanField(
        required=False,
        label="Voglio essere ricontattato",
        help_text="Vuoi ricevere informazioni sulla risoluzione del problema segnalato da chi ha creato il menu?",
    )
    email = forms.EmailField(label="Indirizzo email", required=False)

    class Meta:
        model = MenuReport
        fields = ["name", "message", "get_notified", "email"]

    def clean(self):
        """Validate email field as required only if get_notified is True"""
        cleaned_data = super().clean()
        get_notified = cleaned_data.get("get_notified")
        email = cleaned_data.get("email")
        if get_notified and not email:
            self.add_error(
                "email", "Se vuoi essere ricontattato devi inserire un indirizzo email"
            )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    "name",
                    "message",
                    "get_notified",
                    "email",
                ),
            ),
        )


class ReportFeedbackForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea, label="Messaggio")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    "message",
                ),
            ),
        )
