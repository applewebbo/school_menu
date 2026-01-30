---
# school_menu-chjb
title: 'Fase 1: Foundation - Audit Log & CSP'
status: completed
type: task
priority: normal
created_at: 2026-01-30T08:50:18Z
updated_at: 2026-01-30T08:54:00Z
---

## Obiettivo
Implementare fondamenta per API standardization: AuditLog model, middleware, CSP dependency.

## Checklist
- [x] Aggiungere django-csp>=3.8 a pyproject.toml
- [x] Sync dependencies (uv sync)
- [x] Creare AuditLog model in school_menu/models.py
- [x] Creare e applicare migration
- [x] Aggiungere AuditLogAdmin in school_menu/admin.py
- [x] Creare core/middleware.py con AuditLogMiddleware
- [x] Aggiungere middleware a MIDDLEWARE in settings.py
- [x] Creare test suite: tests/school_menu/test_audit_log.py
- [x] Verificare 100% coverage con just ftest
