---
# school_menu-kie1
title: Fix CSRF error on login (#222)
status: completed
type: bug
priority: normal
created_at: 2026-07-08T07:04:42Z
updated_at: 2026-07-08T07:17:20Z
---

CSRF verification failed on login. Investigate CSRF/CSP/allauth/session cookie config.

## Summary of Changes

Production-only CSRF 403 on login caused by the Coolify reverse proxy terminating TLS: Django saw requests as http, so the CSRF Origin check compared the browser's https Origin against an http scheme and rejected the POST.

Fix: added `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` in core/settings.py so Django treats forwarded requests as HTTPS. Added regression test tests/users/test_csrf.py (TDD red/green).
