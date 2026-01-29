---
# school_menu-lgmd
title: Update imports across codebase
status: todo
type: task
priority: normal
created_at: 2026-01-29T08:54:22Z
updated_at: 2026-01-29T08:55:02Z
parent: school_menu-j8h7
blocking:
    - school_menu-d6fm
---

Update all imports to use new utils structure

## Files to update (9 total)
- [ ] school_menu/management/commands/warm_cache.py
- [ ] school_menu/views.py
- [ ] tests/school_menu/test_utils.py
- [ ] tests/school_menu/test_views.py
- [ ] notifications/utils.py
- [ ] tests/school_menu/test_utils_column_filtering.py
- [ ] tests/notifications/test_utils.py
- [ ] school_menu/resources.py
- [ ] school_menu/management/commands/import_meals.py

## Steps
- [ ] Identify imports in each file
- [ ] Update to specific submodule imports OR keep importing from utils/__init__.py
- [ ] Verify no import errors

## Expected outcome
- All imports updated and working
- No breaking changes for existing code
