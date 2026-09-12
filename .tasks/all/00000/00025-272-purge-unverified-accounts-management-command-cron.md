---
id: '0000000025'
slug: 272-purge-unverified-accounts-management-command-cron
title: '#272: purge unverified accounts management command + cron'
labels: []
created: '2026-09-12T11:51:18.993+02:00'
updated: '2026-09-12T12:12:53.953+02:00'
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-09-12T12:02:14.984+02:00 | Status changed from ready to in-progress |
| 2026-09-12T12:12:53.914+02:00 | purge_unverified_accounts command + users.tasks.purge_unverified_accounts + setup_unverified_account_purge_schedule command, wired into entrypoint.sh as a daily django-q2 cron (default 04:00). Retention 7 days via UNVERIFIED_ACCOUNT_RETENTION_DAYS. |
| 2026-09-12T12:12:53.953+02:00 | Status changed from in-progress to complete |
