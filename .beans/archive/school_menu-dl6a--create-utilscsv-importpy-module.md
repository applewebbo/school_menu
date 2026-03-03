---
# school_menu-dl6a
title: Create utils/csv_import.py module
status: completed
type: task
priority: normal
created_at: 2026-01-29T08:54:18Z
updated_at: 2026-01-29T11:37:00Z
parent: school_menu-j8h7
blocking:
    - school_menu-lgmd
---

Extract CSV import, validation, and widgets into dedicated module

## Functions/classes to move
- detect_csv_format(content: str)
- detect_menu_type(headers: list)
- filter_dataset_columns(dataset, allowed_columns)
- validate_dataset(dataset, menu_type)
- validate_annual_dataset(dataset)
- ChoicesWidget class

## Steps
- [ ] Create utils/csv_import.py
- [ ] Move functions and ChoicesWidget class from utils_old.py
- [ ] Add complete type hints (already partially present)
- [ ] Add module docstring
- [ ] Export functions in utils/__init__.py

## Expected outcome
- csv_import.py with 5 functions, 1 class, and full type hints
- All CSV import/validation logic isolated in one module
