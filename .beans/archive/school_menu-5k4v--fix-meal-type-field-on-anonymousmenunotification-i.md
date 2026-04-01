---
# school_menu-5k4v
title: 'fix: meal_type field on AnonymousMenuNotification (issue #215)'
status: completed
type: bug
priority: normal
created_at: 2026-04-01T05:54:49Z
updated_at: 2026-04-01T06:15:23Z
---

## Summary of Changes\n\n- Added  field to  (default 'S')\n- Migration 0008 (additive, retrocompatible, tutti gli iscritti esistenti ricevono Standard)\n-  ora filtra per meal_type\n- Form mostra il selettore solo se la scuola ha menu alternativi (HiddenInput altrimenti)\n- template subscription_form.html mostra il selettore con Alpine.js condizionale\n- 495 test passano, 100% coverage
