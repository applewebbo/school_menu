---
# school_menu-m76r
title: 'Fase 3: Security - CSP Headers'
status: completed
type: task
priority: normal
created_at: 2026-01-30T09:04:14Z
updated_at: 2026-01-30T09:07:09Z
---

## Obiettivo
Implementare Content Security Policy headers con nonce dinamico per script inline.

## Checklist
- [x] Aggiungere CSP middleware a MIDDLEWARE in settings.py
- [x] Configurare CSP_* settings (default-src, script-src, style-src, etc.)
- [x] Abilitare CSP_REPORT_ONLY=True per modalità non-blocking
- [x] Fix nonce dinamico in templates/base.html per Facebook SDK (line 29)
- [x] Fix nonce dinamico in templates/base.html per Alpine.js script (lines 39-59)
- [x] Creare tests/school_menu/test_csp_headers.py
- [x] Verificare 100% coverage con just ftest
