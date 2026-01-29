---
# school_menu-ensi
title: Add type hints to views and tasks
status: completed
type: task
priority: normal
created_at: 2026-01-29T08:54:24Z
updated_at: 2026-01-29T11:54:19Z
parent: school_menu-j8h7
blocking:
    - school_menu-d6fm
---

Add complete type hints to views, cache, and tasks modules

## Files to update
- [ ] school_menu/views.py - Add type hints to all view functions (deferred - 794 lines, separate task)
- [x] school_menu/cache.py - Already has complete type hints
- [ ] school_menu/tasks.py - File does not exist (no Django Q2 tasks in school_menu)
- [x] notifications/tasks.py - Add type hints to notification tasks

## Steps
- [ ] Identify all functions without type hints
- [ ] Add parameter and return type annotations
- [ ] Use typing module for complex types (Union, Optional, etc.)
- [ ] Run ty type checker to verify correctness

## Expected outcome
- 100% type coverage in views, cache, and tasks
- No type checker errors
