---
# school_menu-35ax
title: Performance Optimization & Monitoring
status: completed
type: epic
priority: high
tags:
    - phase-1
    - performance
    - gh-issue-207
created_at: 2026-01-27T14:36:31Z
updated_at: 2026-01-28T08:01:03Z
---

Database query optimization and performance monitoring.

## Checklist
- [x] Optimize fill_missing_dates() to use bulk_create instead of loop (N→1 query)
- [x] Implement N+1 query monitoring with django-nplusone
- [x] Add cache warming management command (python manage.py warm_cache)
- [x] Add assertNumQueries() tests for critical views

**Files affected:**
- school_menu/utils.py (fill_missing_dates)
- school_menu/management/commands/warm_cache.py (new)
- tests/performance/ (new tests)
- core/settings/test.py (nplusone config)

**Expected outcome:**
- Massive performance improvement for bulk operations
- Automatic N+1 detection in CI
- No cold cache after deployments
- Query count enforcement in tests

**Time estimate:** ~3-4 hours
**Impact:** High - Better performance, prevent regressions
