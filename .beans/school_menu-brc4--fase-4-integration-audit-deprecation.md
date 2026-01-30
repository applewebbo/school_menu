---
# school_menu-brc4
title: 'Fase 4: Integration - Audit & Deprecation'
status: completed
type: task
priority: normal
created_at: 2026-01-30T09:10:50Z
updated_at: 2026-01-30T10:02:49Z
---

## Obiettivo
Integrare audit logging nelle view CRUD e aggiungere deprecation headers ai legacy endpoints.

## Checklist
- [ ] Aggiungere audit_log in school_create view (dopo save)
- [ ] Aggiungere audit_log in school_update view (se form.has_changed)
- [ ] Aggiungere audit_log in school_delete view
- [ ] Aggiungere audit_log in upload_menu view (dopo import)
- [ ] Aggiungere deprecation headers in get_schools_json_list
- [ ] Aggiungere deprecation headers in get_school_json_menu
- [ ] Creare tests per audit logging integration
- [ ] Creare tests per deprecation headers
- [ ] Verificare 100% coverage con just ftest
