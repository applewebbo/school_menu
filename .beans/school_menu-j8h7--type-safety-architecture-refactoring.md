---
# school_menu-j8h7
title: Type Safety & Architecture Refactoring
status: in-progress
type: epic
priority: normal
tags:
    - phase-2
    - architecture
    - gh-issue-208
created_at: 2026-01-27T14:36:43Z
updated_at: 2026-01-29T11:31:50Z
blocking:
    - school_menu-izm5
---

Type hints and module organization improvements.

**Tasks:**
1. Add complete type hints throughout codebase (utils, views, cache, tasks)
2. Split monolithic utils.py (19KB) into specialized modules:
   - school_menu/utils/calendar.py
   - school_menu/utils/meals.py
   - school_menu/utils/csv_import.py
   - school_menu/utils/notifications.py

**Files affected:**
- school_menu/utils.py → school_menu/utils/ package
- All files importing from utils (update imports)
- Type annotations added to: utils, views, cache, tasks

**Expected outcome:**
- Full type safety with mypy/ty
- Better IDE autocomplete
- Clearer module responsibilities
- Easier navigation and testing

**Time estimate:** ~4-5 hours
**Impact:** Medium - Long-term maintainability
**Blocked by:** Code Quality epic completion
