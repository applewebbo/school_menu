from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render

from contacts.forms import ContactForm, MenuReportForm
from school_menu.models import School


def contact(request):
    print("Request method:", request.method)
    print("POST data:", request.POST)
    print("Headers:", request.headers)
    form = ContactForm(request.POST or None)
    print("Form errors:", form.errors)
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


def menu_report(request, school_id):
    school = get_object_or_404(School, id=school_id)
    form = MenuReportForm(request.POST or None)
    if form.is_valid():
        report = form.save(commit=False)
        report.receiver = school.user
        report.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Messaggio inviato con successo",
        )
        return redirect("school_menu:school_menu", school.slug)

    context = {"form": form, "school": school}
    return render(request, "contacts/menu-report.html", context)
