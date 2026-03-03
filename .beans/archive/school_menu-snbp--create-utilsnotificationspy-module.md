---
# school_menu-snbp
title: Create utils/notifications.py module
status: completed
type: task
priority: normal
created_at: 2026-01-29T08:54:20Z
updated_at: 2026-01-29T11:39:24Z
parent: school_menu-j8h7
blocking:
    - school_menu-lgmd
---

Extract notification utilities into dedicated module

## Functions to move
- get_notifications_status(pk, school)

## Steps
- [ ] Create utils/notifications.py
- [ ] Move function from utils_old.py
- [ ] Add complete type hints
- [ ] Add module docstring
- [ ] Export function in utils/__init__.py

## Expected outcome
- notifications.py with 1 function and full type hints
- Notification logic isolated for future expansion
