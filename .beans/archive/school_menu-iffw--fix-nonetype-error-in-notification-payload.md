---
# school_menu-iffw
title: Fix NoneType error in notification payload
status: completed
type: bug
priority: normal
created_at: 2026-03-02T13:31:46Z
updated_at: 2026-03-02T13:35:36Z
---

notifications/tasks.py line 173 crashes when build_menu_notification_payload returns None (no meals). Add None guard and skip notification.

## Summary of Changes\n\nAdded None guard in `_send_menu_notifications` after calling `build_menu_notification_payload`. When no meals exist for a school, the function returns None and the notification is now silently skipped with a log message instead of crashing with TypeError. Added a test to cover this scenario.
