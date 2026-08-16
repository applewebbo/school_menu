"""
Background work for the AI menu import (#234).

The task is written to be safe under redelivery: django-q re-queues a task whose `retry`
window elapses, and a second extraction would both cost another call and overwrite rows
the user may already be editing. Every transition is therefore guarded on the status the
draft is expected to be in, and the draft always ends in a terminal state — a draft stuck
in PENDING is a preview page that polls forever.
"""

import logging

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from django_q.tasks import async_task

from school_menu.ai.errors import AIImportError
from school_menu.ai.extraction import extract_menu
from school_menu.models import MenuImportDraft
from school_menu.services import ai_quota
from school_menu.utils.support import log_unexpected, support_hint

logger = logging.getLogger(__name__)

TASK_PATH = "school_menu.tasks.process_menu_import_draft"


def _finish(draft, **fields):
    """
    Write the outcome, but only if the draft is still the one we started working on.

    A guarded UPDATE rather than `save()`: if the user cancelled in the meantime, or a
    duplicate delivery already finished the job, the late writer must not win.
    """
    return MenuImportDraft.objects.filter(
        pk=draft.pk, status=MenuImportDraft.Status.PENDING
    ).update(completed_at=timezone.now(), **fields)


def _discard_file(draft):
    """Drop the uploaded file: it has been read, and menus may carry third-party data."""
    if draft.source_file:
        draft.source_file.delete(save=False)
        MenuImportDraft.objects.filter(pk=draft.pk).update(source_file="")


def process_menu_import_draft(draft_id):
    """Extract the menu of a PENDING draft and store the result on it."""
    draft = MenuImportDraft.objects.filter(
        pk=draft_id, status=MenuImportDraft.Status.PENDING
    ).first()
    if draft is None:
        return

    try:
        try:
            content = draft.source_file.read()
            result = extract_menu(
                draft.kind, content, draft.source_filename, season=draft.season
            )
        except AIImportError:
            raise
        except Exception as exc:
            # Never let something unforeseen leave the draft PENDING: the user would be
            # left polling a preview that never arrives. The detail stays in the log,
            # reachable through the code the user is shown (#251).
            code = log_unexpected(
                logger, "Menu import draft %s failed unexpectedly", draft_id
            )
            raise AIImportError(
                str(exc),
                user_message=(f"{AIImportError.user_message} {support_hint(code)}"),
            ) from exc
    except AIImportError as error:
        if error.refundable:
            ai_quota.refund(draft.user)
        _finish(
            draft,
            status=MenuImportDraft.Status.FAILED,
            error_code=error.code,
            error_message=error.user_message,
        )
    else:
        _finish(
            draft,
            status=MenuImportDraft.Status.READY,
            rows=result.rows,
            warnings=result.warnings,
            usage=result.usage,
        )
    finally:
        _discard_file(draft)


def purge_menu_import_drafts():
    """
    Entry point for the scheduled retention run.

    django-q schedules point at a dotted path, so the schedule targets this rather than
    the management command: the command stays the manual, inspectable way in (it has
    --dry-run), and the schedule keeps a stable path even if the command is renamed.
    """
    call_command("purge_menu_imports", verbosity=0)


def queue_menu_import(draft):
    """
    Charge the quota and hand the draft to the worker.

    Raises:
        QuotaExceeded: nothing is queued and the draft stays OFFERED, so the user can
            still fall back to a CSV upload with the file they already provided.
    """
    ai_quota.consume(draft.user)
    draft.status = MenuImportDraft.Status.PENDING
    draft.save(update_fields=["status", "updated_at"])
    draft.task_id = async_task(
        TASK_PATH, draft.pk, timeout=settings.AI_MENU_IMPORT_TASK_TIMEOUT
    )
    MenuImportDraft.objects.filter(pk=draft.pk).update(task_id=draft.task_id)
    return draft.task_id
