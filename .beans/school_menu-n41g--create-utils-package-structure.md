---
# school_menu-n41g
title: Create utils package structure
status: todo
type: task
priority: normal
created_at: 2026-01-29T08:54:10Z
updated_at: 2026-01-29T09:01:58Z
parent: school_menu-j8h7
blocking:
    - school_menu-ow4m
    - school_menu-8jn8
    - school_menu-dl6a
    - school_menu-snbp
---

Convert school_menu/utils.py into school_menu/utils/ package

## Steps
- [ ] Rename utils.py to utils_old.py temporarily
- [ ] Create utils/ directory
- [ ] Create utils/__init__.py with re-exports of all functions for backwards compatibility
- [ ] Verify imports still work

## Expected outcome
- utils/ package created
- Backwards compatible __init__.py maintains all existing imports
