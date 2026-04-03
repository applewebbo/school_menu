---
# school_menu-0hlo
title: Migrate backup storage from Dropbox to OVHcloud Object Storage
status: in-progress
type: task
priority: high
created_at: 2026-03-20T10:11:54Z
updated_at: 2026-04-03T07:47:38Z
---

Migrate django-dbbackup storage from Dropbox to OVHcloud Object Storage (S3-compatible). Server already on OVHcloud, same provider, EU data residency, no OAuth token expiry issues.

**Codeberg Issue**: #214
**Branch**: feature/migrate-backup-ovhcloud-s3

## Context

Current setup:
- Storage: Dropbox via `storages.backends.dropbox.DropBoxStorage`
- Dependencies: `django-storages[dropbox]`
- Settings: 4 env vars (DROPBOX_OAUTH2_ACCESS_TOKEN, DROPBOX_OAUTH2_REFRESH_TOKEN, DROPBOX_APP_SECRET, DROPBOX_APP_KEY)
- `boto3` not yet installed

Target:
- Storage: OVHcloud Object Storage (S3-compatible) via `storages.backends.s3boto3.S3Boto3Storage`
- Dependencies: `django-storages[s3]` + `boto3` (replaces `django-storages[dropbox]`)
- Settings: 5 env vars (OVH_S3_ACCESS_KEY, OVH_S3_SECRET_KEY, OVH_S3_BUCKET_NAME, OVH_S3_ENDPOINT_URL, OVH_S3_REGION)

## Tasks

### 1. Setup OVHcloud Object Storage
- [ ] Create Object Storage container in OVHcloud control panel (region EU, e.g. GRA)
- [ ] Generate S3 credentials (Access Key + Secret Key) from OVHcloud panel
- [ ] Note endpoint URL (e.g. https://s3.gra.perf.cloud.ovh.net)
- [ ] Note bucket name

### 2. Dependencies
- [x] Add `boto3` and `django-storages[s3]` to pyproject.toml
- [x] Remove `django-storages[dropbox]` from pyproject.toml
- [x] Run `just install` to sync deps

### 3. Settings update (core/settings.py)
- [x] Replace `STORAGES["dbbackup"]` backend from `DropBoxStorage` to `S3Boto3Storage`
- [x] Replace Dropbox OPTIONS with S3 options:
  - `access_key` ← env("OVH_S3_ACCESS_KEY")
  - `secret_key` ← env("OVH_S3_SECRET_KEY")
  - `bucket_name` ← env("OVH_S3_BUCKET_NAME")
  - `endpoint_url` ← env("OVH_S3_ENDPOINT_URL")
  - `region_name` ← env("OVH_S3_REGION", default="gra")
  - `default_acl` ← "private"

### 4. env.example update
- [x] Add OVH_S3_ACCESS_KEY, OVH_S3_SECRET_KEY, OVH_S3_BUCKET_NAME, OVH_S3_ENDPOINT_URL, OVH_S3_REGION
- [x] Remove DROPBOX_* variables

### 5. Tests
- [x] Aggiorna test backup esistenti con il nuovo storage mock S3
- [x] Esegui `just ftest` → 100% coverage

### 6. Production deployment
- [ ] Ask user to add OVH_S3_* variables to production .env
- [ ] Ask user to remove DROPBOX_* variables from production .env
- [ ] Deploy
- [ ] Trigger manual backup from Django admin (Backup Runs → action)
- [ ] Verify file appears in OVHcloud Object Storage container
- [ ] Test restore: `python manage.py dbrestore`

## Notes

- OVHcloud S3 endpoint format: `https://s3.<region>.perf.cloud.ovh.net` (high-perf) or `https://s3.<region>.cloud.ovh.net` (standard)
- `django-storages` S3Boto3Storage requires `boto3` but NOT `s3transfer` extra if boto3 is installed separately
- Set `default_acl` to `"private"` to prevent public access to backup files
- `DBBACKUP_FILENAME_TEMPLATE` stays unchanged (MenuAppCloud-{datetime}.{extension})
