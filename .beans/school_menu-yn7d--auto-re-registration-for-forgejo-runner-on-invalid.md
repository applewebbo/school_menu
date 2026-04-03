---
# school_menu-yn7d
title: Auto re-registration for Forgejo runner on invalid token
status: in-progress
type: task
priority: normal
created_at: 2026-04-02T18:47:17Z
updated_at: 2026-04-03T07:52:30Z
---

Add healthcheck or restart logic to forgejo-runner docker-compose to automatically delete .runner file and re-register when the token becomes invalid (502 Bad Gateway loop). Currently requires manual intervention to fix.

**Codeberg Issue**: #217
**Branch**: 2026.1.4
