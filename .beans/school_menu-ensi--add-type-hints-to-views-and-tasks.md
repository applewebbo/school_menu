---
# school_menu-ensi
title: Add type hints to views and tasks
status: todo
type: task
priority: normal
created_at: 2026-01-29T08:54:24Z
updated_at: 2026-01-29T08:55:02Z
parent: school_menu-j8h7
blocking:
    - school_menu-d6fm
---

Add complete type hints to views, cache, and tasks modules

## Files to update
- [ ] school_menu/views.py - Add type hints to all view functions
- [ ] school_menu/cache.py - Add type hints to cache utilities
- [ ] school_menu/tasks.py - Add type hints to Django Q2 tasks
- [ ] notifications/tasks.py - Add type hints to notification tasks

## Steps
- [ ] Identify all functions without type hints
- [ ] Add parameter and return type annotations
- [ ] Use typing module for complex types (Union, Optional, etc.)
- [ ] Run ty type checker to verify correctness

## Expected outcome
- 100% type coverage in views, cache, and tasks
- No type checker errors
