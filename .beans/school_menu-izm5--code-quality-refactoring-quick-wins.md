---
# school_menu-izm5
title: Code Quality & Refactoring (Quick Wins)
status: in-progress
type: epic
priority: high
tags:
    - quick-wins
    - gh-issue-206
    - phase-1
created_at: 2026-01-27T14:36:16Z
updated_at: 2026-01-28T06:50:33Z
---

Improvements to code quality, maintainability and documentation.

## Checklist
- [x] Create constants.py with all magic numbers (cache TTLs, equinox dates, etc.)
- [x] Replace all print() statements with proper logging
- [ ] Refactor duplicate code in index() and school_menu() views
- [ ] Add missing docstrings to all views
- [ ] Consolidate CSV error handling with decorator or shared function

**Files affected:**
- school_menu/constants.py (new)
- school_menu/views.py
- school_menu/cache.py
- school_menu/utils.py

**Expected outcome:**
- Self-documenting code with named constants
- Structured logging instead of print()
- DRY principles applied
- Complete documentation

**Time estimate:** ~3-4 hours
**Impact:** High - Easier maintenance, better debugging
