import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from contacts.forms import ContactForm, MenuReportForm, ReportFeedbackForm
from contacts.models import MenuReport
from school_menu.models import School

logger = logging.getLogger(__name__)


def contact(request):
    form = ContactForm(request.POST or None)
    if form.is_valid():
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        message = form.cleaned_data["message"]
        send_mail(
            f"Contatto da {name} su menuscolastico.it",
            f"{message}\n\nRispondi a {email}",
            None,
            ["e.bonardi@me.com"],
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
        # The report is already saved: a mail-provider blip here must not lose it or
        # break the response, only be recorded so the monthly admin digest can surface
        # it (#280).
        try:
            send_mail(
                f"Segnalazione ricevuta da {name} su menuscolastico.it",
                message,
                None,
                [email],
            )
        except Exception as e:
            logger.error(f"Failed to send menu report notification for {name}: {e}")
            report.notification_error = str(e)
            report.save(update_fields=["notification_error"])
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


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(MenuReport, id=report_id, receiver=request.user)
    context = {"report": report}
    return render(request, "contacts/report-detail.html", context)


@login_required
def report_feedback(request, report_id):
    # Scoped to the receiver: without it any logged-in account could make the site send an
    # arbitrary message, from our own address, to the email on somebody else's report (#246).
    report = get_object_or_404(MenuReport, id=report_id, receiver=request.user)
    form = ReportFeedbackForm(request.POST or None)
    if form.is_valid():
        message = form.cleaned_data["message"]
        try:
            send_mail(
                f"Risposta a segnalazione ricevuta da {report.name} su menuscolastico.it",
                message,
                None,
                [report.email],
            )
        except Exception as e:
            logger.error(f"Failed to send feedback reply for report {report.pk}: {e}")
            messages.error(request, f"Errore durante l'invio della risposta: {e}")
            return redirect(reverse("school_menu:settings"))
        report.feedback_sent_at = timezone.now()
        report.save(update_fields=["feedback_sent_at"])
        messages.add_message(
            request,
            messages.SUCCESS,
            "Risposta inviata con successo",
        )
        return redirect(reverse("school_menu:settings"))
    context = {"form": form, "report": report}
    return render(request, "contacts/report-feedback.html", context)


@login_required
@require_http_methods(["POST"])
def report_delete(request, report_id):
    # Ownership in the query rather than in an `if`, like the other two views: the same
    # shape everywhere is what makes a missing check visible on sight (#246).
    report = get_object_or_404(MenuReport, id=report_id, receiver=request.user)
    report.delete()

    reports = MenuReport.objects.filter(receiver=request.user)
    context = {"reports": reports}
    response = render(request, "contacts/report-list.html", context)
    response["HX-Trigger"] = "reportDeleted"
    return response
