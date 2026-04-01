---
# school_menu-0hlo
title: Migrate backup storage from Dropbox to OVHcloud Object Storage
status: todo
type: task
priority: high
created_at: 2026-03-20T10:11:54Z
updated_at: 2026-03-20T10:13:27Z
---

Migrate django-dbbackup storage from Dropbox to OVHcloud Object Storage (S3-compatible). Server already on OVHcloud, same provider, EU data residency, no OAuth token expiry issues.

**Codeberg Issue**: #214
**Branch**: 2026.1.2

## Context

Current setup:
- Storage: Dropbox via
- Dependencies:
- Settings: 4 env vars (oauth2_access_token, oauth2_refresh_token, app_secret, app_key)
-  not yet installed

Target:
- Storage: OVHcloud Object Storage (S3-compatible) via
- Dependencies:  (replaces )
- Settings: 4 env vars (endpoint_url, access_key, secret_key, bucket_name)

## Tasks

### 1. Setup OVHcloud Object Storage
- [ ] Create Object Storage container in OVHcloud control panel (region EU, e.g. GRA)
- [ ] Generate S3 credentials (Access Key + Secret Key) from OVHcloud panel
- [ ] Note endpoint URL (e.g. https://s3.gra.perf.cloud.ovh.net)
- [ ] Note bucket name

### 2. Dependencies
- [ ] Add  to pyproject.toml
- [ ] Remove  from pyproject.toml
- [ ] Run  to sync deps

### 3. Settings update (core/settings.py)
- [ ] Replace STORAGES["dbbackup"] backend from DropBoxStorage to S3Boto3Storage
- [ ] Replace Dropbox OPTIONS with S3 options:
  -  ← env("OVH_S3_ACCESS_KEY")
  -  ← env("OVH_S3_SECRET_KEY")
  -  ← env("OVH_S3_BUCKET_NAME")
  -  ← env("OVH_S3_ENDPOINT_URL")
  -  ← env("OVH_S3_REGION", default="gra")
  -  ← "private"

### 4. env.example update
- [ ] Add OVH_S3_ACCESS_KEY, OVH_S3_SECRET_KEY, OVH_S3_BUCKET_NAME, OVH_S3_ENDPOINT_URL, OVH_S3_REGION
- [ ] Remove DROPBOX_* variables (or mark as deprecated)

### 5. Tests
- [ ] Check existing backup tests still pass with new storage mock
- [ ] Run ============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-8.3.5, pluggy-1.6.0
benchmark: 5.2.3 (defaults: timer=time.perf_counter disable_gc=False min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=100000)
django: version: 6.0.3, settings: core.settings (from ini)
rootdir: /Users/enricobonardi/CODING/WEBBO_PROJECTS/school_menu
configfile: pyproject.toml
testpaths: tests
plugins: benchmark-5.2.3, locust-2.43.3, django-test-plus-2.4.1, xdist-3.8.0, time-machine-3.2.0, Faker-40.5.1, monitor-1.6.6, django-4.12.0, factoryboy-2.8.1, cov-7.0.0
created: 8/8 workers
8 workers [491 items]

........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 87%]
...........................................................              [100%]
================================ tests coverage ================================
_______________ coverage: platform darwin, python 3.14.2-final-0 _______________

Name    Stmts   Miss Branch BrPart  Cover
-----------------------------------------
TOTAL    1792      0    324      0   100%

44 files skipped due to complete coverage.
Coverage HTML written to dir htmlcov
Required test coverage of 100% reached. Total coverage: 100.00%
============================= 491 passed in 35.01s ============================= → 100% coverage

### 6. Production deployment
- [ ] Ask user to add OVH_S3_* variables to production .env
- [ ] Ask user to remove DROPBOX_* variables from production .env
- [ ] Deploy
- [ ] Trigger manual backup from Django admin (Backup Runs → action)
- [ ] Verify file appears in OVHcloud Object Storage container
- [ ] Test restore:

## Notes

- OVHcloud S3 endpoint format:  (high-perf) or  (standard)
- django-storages S3Boto3Storage requires  but NOT  extra if boto3 is installed separately
- Set  to prevent public access to backup files
- DBBACKUP_FILENAME_TEMPLATE stays unchanged (MenuAppCloud-{datetime}.{extension})
