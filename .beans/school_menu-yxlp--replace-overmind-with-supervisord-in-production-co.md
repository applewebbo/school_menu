---
# school_menu-yxlp
title: Replace Overmind with supervisord in production container
status: in-progress
type: task
priority: normal
created_at: 2026-04-10T09:02:28Z
updated_at: 2026-04-12T09:19:35Z
---

Sostituire Overmind con supervisord per gestire i processi gunicorn e qcluster in produzione, risolvendo il problema di riavvio dopo reboot del VPS

## Todo

- [ ] Installare supervisord nel Dockerfile
- [ ] Creare supervisord.conf con programmi gunicorn e qcluster
- [ ] Aggiornare entrypoint.sh per avviare supervisord invece di overmind
- [ ] Rimuovere dipendenza da overmind

Codeberg issue: #218
