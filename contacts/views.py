from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from .forms import ContactForm


def contact(request):
    form = ContactForm(request.POST or None)
    if form.is_valid():
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        message = form.cleaned_data["message"]
        send_mail(
            f"Contatto da {name} su menu.webbografico.com",
            f"{message}\n\nRispondi a {email}",
            None,
            ["e.bonardi@me.com"],
            fail_silently=False,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "Messaggio inviato con successo",
        )
        return redirect("school_menu:index")

    context = {"form": form, "create": True}
    return render(request, "contacts/contact.html", context)
