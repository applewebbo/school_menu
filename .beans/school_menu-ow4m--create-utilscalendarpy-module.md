---
# school_menu-ow4m
title: Create utils/calendar.py module
status: todo
type: task
priority: normal
created_at: 2026-01-29T08:54:15Z
updated_at: 2026-01-29T08:55:02Z
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
- [ ] Create utils/calendar.py
- [ ] Move functions from utils_old.py
- [ ] Add complete type hints
- [ ] Add module docstring
- [ ] Export functions in utils/__init__.py

## Expected outcome
- calendar.py with 4 functions and full type hints
- All calendar logic isolated in one module
