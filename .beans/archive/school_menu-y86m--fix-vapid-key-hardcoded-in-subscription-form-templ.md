---
# school_menu-y86m
title: 'fix: VAPID key hardcoded in subscription form template'
status: completed
type: bug
priority: normal
created_at: 2026-03-17T13:55:55Z
updated_at: 2026-03-17T14:08:05Z
---

After server migration with different SECRET_KEY, sessions are lost. Users without subscription_endpoint cookie see the subscription form. The VAPID public key is hardcoded in subscription_form.html:33 instead of being read from WEBPUSH_SETTINGS. This should be fixed to use the server-side value.

## Summary of Changes

- Added `from django.conf import settings` import to `notifications/views.py`
- Pass `vapid_public_key` from `WEBPUSH_SETTINGS` in context of `notification_settings` and `save_subscription` (error case) views
- Updated `subscription_form.html` to use `{{ vapid_public_key }}` instead of hardcoded string
- Added 2 tests to verify `vapid_public_key` is present in view contexts
