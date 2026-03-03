---
# school_menu-ow4m
title: Create utils/calendar.py module
status: completed
type: task
priority: normal
created_at: 2026-01-29T08:54:15Z
updated_at: 2026-01-29T11:34:36Z
parent: school_menu-j8h7
blocking:
    - school_menu-lgmd
---

Extract calendar and date utilities into dedicated module

## Functions to move
- calculate_week(week, bias)
- get_current_date(next_day=False)
- get_season(school)
- get_adjusted_year()

## Steps
- [x] Create utils/calendar.py
- [x] Move functions from utils_old.py
- [x] Add complete type hints
- [x] Add module docstring
- [x] Export functions in utils/__init__.py

## Expected outcome
- calendar.py with 4 functions and full type hints
- All calendar logic isolated in one module
