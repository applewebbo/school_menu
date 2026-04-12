---
# school_menu-yxlp
title: Replace Overmind with supervisord in production container
status: completed
type: task
priority: normal
created_at: 2026-04-10T09:02:28Z
updated_at: 2026-04-12T09:21:02Z
---

Sostituire Overmind con supervisord per gestire i processi gunicorn e qcluster in produzione, risolvendo il problema di riavvio dopo reboot del VPS

## Todo

- [x] Installare supervisord nel Dockerfile
- [x] Creare supervisord.conf con programmi gunicorn e qcluster
- [x] Aggiornare entrypoint.sh per avviare supervisord invece di overmind
- [x] Rimuovere dipendenza da overmind

Codeberg issue: #218

## Summary of Changes

- Sostituito overmind con supervisord (installato via apt)
- Creato `supervisord.conf` con programmi `web` (gunicorn) e `worker` (qcluster), con autorestart e log separati
- Aggiornato `entrypoint.sh` per avviare supervisord
- Rimosso download e installazione di overmind dal Dockerfile
