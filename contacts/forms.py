from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Nome")
    email = forms.EmailField(label="Indirizzo email")
    message = forms.CharField(widget=forms.Textarea, label="Messaggio")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
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
