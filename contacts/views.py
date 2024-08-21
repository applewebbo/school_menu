from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ContactForm


def contact(request):
    form = ContactForm(request.POST or None)
    if form.is_valid():
        school = form.save(commit=False)
        school.user = request.user
        school.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Messaggio inviato con successo",
        )
        return redirect("school_menu:index")

    context = {"form": form, "create": True}
    return render(request, "contacts/contact.html", context)
