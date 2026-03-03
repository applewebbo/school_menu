---
# school_menu-8jn8
title: Create utils/meals.py module
status: completed
type: task
priority: normal
created_at: 2026-01-29T08:54:17Z
updated_at: 2026-01-29T11:39:24Z
parent: school_menu-j8h7
blocking:
    - school_menu-lgmd
---

Extract meal retrieval and menu building utilities into dedicated module

## Functions to move
- get_user(pk)
- get_alt_menu(user)
- build_types_menu(weekly_meals, school, week=None, season=None)
- get_meals(school, season, week, day)
- get_meals_for_annual_menu(school, next_day=False)
- fill_missing_dates(school, meal_type)

## Steps
- [ ] Create utils/meals.py
- [ ] Move functions from utils_old.py
- [ ] Add complete type hints
- [ ] Add module docstring
- [ ] Export functions in utils/__init__.py

## Expected outcome
- meals.py with 6 functions and full type hints
- All meal-related logic isolated in one module
