from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render

from contacts.forms import ContactForm, MenuReportForm
from contacts.models import MenuReport
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
        name = report.name
        email = report.receiver
        if report.get_notified:
            message = f"{report.message}\n\n{name} ha chiesto di poter ricevere una risposta alla sua segnalazione. Puoi farlo entro 30gg nella sezione Account/Visualizza segnalazioni del tuo profilo."
        else:
            message = f"{report.message}"
        send_mail(
            f"Segnalazione ricevuta da {name} su menu.webbografico.com",
            message,
            None,
            [email],
            fail_silently=False,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "Segnalazione inviata con successo",
        )
        return redirect("school_menu:school_menu", school.slug)

    context = {"form": form, "school": school}
    return render(request, "contacts/menu-report.html", context)


@login_required
def report_list(request):
    reports = MenuReport.objects.filter(receiver=request.user)
    context = {"reports": reports}
    return render(request, "contacts/report-list.html", context)
