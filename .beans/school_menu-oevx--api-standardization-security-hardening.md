---
# school_menu-oevx
title: API Standardization & Security Hardening
status: todo
type: epic
priority: normal
tags:
    - phase-3
    - security
    - api
    - gh-issue-209
created_at: 2026-01-27T14:36:56Z
updated_at: 2026-01-27T14:41:48Z
---

REST API improvements and security enhancements.

**Tasks:**
1. Implement Django REST Framework API with ViewSets
   - Automatic pagination, throttling, schema generation
   - Replace custom JSON endpoints
2. Add rate limiting to public APIs (django-ratelimit)
   - 100 req/hour for anonymous users
   - Custom 429 error pages
3. Implement Content Security Policy headers (django-csp)
   - XSS protection
   - External resource whitelisting
4. Create audit log system for critical operations
   - Track CRUD on schools, menus, settings
   - Store user, action, changes, IP, timestamp

**Files affected:**
- school_menu/api/ (new package with views, serializers, urls)
- core/settings/base.py (CSP config)
- core/audit.py (new AuditLog model)
- core/middleware.py (audit middleware)

**Expected outcome:**
- Professional REST API with auto-documentation
- Protection against API abuse
- Enhanced XSS protection
- Complete audit trail

**Time estimate:** ~6-8 hours
**Impact:** Medium-High - Security, compliance, API quality
