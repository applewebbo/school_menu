# Django Scheduled Backups

A reusable Django app for scheduling database and media backups with email notifications and history tracking.

## Features

- **Automated Backups**: Schedule database and media backups using Django-Q2 or Celery
- **Email Notifications**: Get notified on backup success or failure
- **History Tracking**: Track all backup runs in the database with status, duration, and error details
- **Admin Interface**: View and manage backup history through Django admin
- **Configurable**: Flexible settings for schedules, notifications, and retention
- **Management Command**: Easy setup with `setup_backup_schedules` command
- **Manual Triggers**: Trigger backups manually from Django admin
- **Automatic Cleanup**: Configurable retention policy for backup history

## Requirements

- Django >= 5.0
- django-dbbackup >= 4.0
- django-q2 >= 1.0 (or Celery)
- croniter >= 6.0
- Storage backend configured (e.g., Dropbox, S3, etc.)

## Installation

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... other apps
    "django_scheduled_backups",
    # ...
]
```

### 2. Configure Settings

Add to your `settings.py`:

```python
SCHEDULED_BACKUPS = {
    # Enable/disable the backup system
    "ENABLED": True,

    # Email addresses to notify (falls back to ADMINS if not set)
    "NOTIFICATION_EMAILS": ["admin@example.com"],

    # Database backup configuration
    "DATABASE_BACKUP": {
        "enabled": True,
        "schedule": "0 2 * * *",  # Daily at 2 AM
    },

    # Media backup configuration
    "MEDIA_BACKUP": {
        "enabled": False,
        "schedule": "0 3 * * 0",  # Weekly on Sunday at 3 AM
    },

    # How many days to keep backup history records
    "HISTORY_RETENTION_DAYS": 90,

    # Send email on successful backup
    "EMAIL_ON_SUCCESS": True,

    # Send email on failed backup
    "EMAIL_ON_FAILURE": True,

    # Task queue backend: 'django_q' or 'celery'
    "TASK_QUEUE": "django_q",

    # Email subject prefix
    "EMAIL_SUBJECT_PREFIX": "[Backup]",
}
```

### 3. Run Migrations

```bash
python manage.py migrate django_scheduled_backups
```

### 4. Setup Backup Schedules

```bash
python manage.py setup_backup_schedules
```

This will create the scheduled tasks in Django-Q2 (or Celery).

## Usage

### Viewing Backup History

Navigate to **Django Admin → Scheduled Backups → Backup Runs** to view the history of all backup runs.

### Manual Backup Triggers

From the Backup Runs admin page:
1. Select any backup runs (selection doesn't matter)
2. Choose action: "Trigger database backup now" or "Trigger media backup now"
3. Click "Go"

### Cleanup Old Records

From the Backup Runs admin page:
1. Select any backup runs (selection doesn't matter)
2. Choose action: "Cleanup old backup records"
3. Click "Go"

This will delete backup history records older than `HISTORY_RETENTION_DAYS`.

### Management Commands

#### Setup schedules
```bash
# Create or update backup schedules
python manage.py setup_backup_schedules

# Dry run (show what would be done)
python manage.py setup_backup_schedules --dry-run

# Remove existing schedules
python manage.py setup_backup_schedules --remove
```

## Email Notifications

### Success Email Format

**Subject**: `[Backup] Database Backup Successful - 2025-10-26 02:00:00`

**Body**:
```
Database backup completed successfully.

Timestamp: 2025-10-26 02:00:00
Duration: 45 seconds
Environment: prod
Storage Backend: storages.backends.dropbox.DropBoxStorage

This is an automated message from the Django Scheduled Backups system.
```

### Failure Email Format

**Subject**: `[Backup] Database Backup FAILED - 2025-10-26 02:00:00`

**Body**:
```
⚠️ DATABASE BACKUP FAILED ⚠️

Timestamp: 2025-10-26 02:00:00
Environment: prod
Error: [error message]

Please investigate this issue immediately.
Check the Django admin for full error details and traceback.

Backup Run ID: 123

This is an automated message from the Django Scheduled Backups system.
```

## Configuration Reference

### Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ENABLED` | bool | `True` | Enable/disable the backup system |
| `NOTIFICATION_EMAILS` | list | `None` | Email addresses to notify (falls back to ADMINS) |
| `DATABASE_BACKUP.enabled` | bool | `True` | Enable database backups |
| `DATABASE_BACKUP.schedule` | str | `"0 2 * * *"` | Cron expression for database backup schedule |
| `MEDIA_BACKUP.enabled` | bool | `False` | Enable media backups |
| `MEDIA_BACKUP.schedule` | str | `"0 3 * * 0"` | Cron expression for media backup schedule |
| `HISTORY_RETENTION_DAYS` | int | `90` | Days to keep backup history records |
| `EMAIL_ON_SUCCESS` | bool | `True` | Send email on successful backup |
| `EMAIL_ON_FAILURE` | bool | `True` | Send email on failed backup |
| `TASK_QUEUE` | str | `"django_q"` | Task queue backend ('django_q' or 'celery') |
| `EMAIL_SUBJECT_PREFIX` | str | `"[Backup]"` | Email subject prefix |

### Cron Expression Examples

Common backup schedules:

- `0 2 * * *` - Daily at 2:00 AM
- `0 3 * * 0` - Weekly on Sunday at 3:00 AM
- `0 1 * * 1-5` - Weekdays at 1:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 1 * *` - Monthly on 1st at midnight

See [crontab.guru](https://crontab.guru/) for help creating cron expressions.

## Task Functions

You can also call the backup functions directly:

```python
from django_scheduled_backups.tasks import (
    scheduled_database_backup,
    scheduled_media_backup,
)

# Trigger database backup
scheduled_database_backup()

# Trigger media backup
scheduled_media_backup()
```

## Models

### BackupRun

Tracks backup execution history.

**Fields**:
- `backup_type`: "database" or "media"
- `status`: "running", "success", or "failed"
- `started_at`: When the backup started
- `completed_at`: When the backup completed
- `duration_seconds`: How long the backup took
- `error_message`: Error details if backup failed

## Admin Interface

The BackupRun admin provides:

- **List View**: Shows all backups with colored status badges
- **Filters**: Filter by status, type, and date
- **Search**: Search error messages
- **Actions**:
  - Trigger database backup now
  - Trigger media backup now
  - Cleanup old backup records
- **Read-only**: Cannot manually create or edit backup runs

## Advantages Over Cron

1. **Centralized Management**: Schedules managed in Django admin, no server access needed
2. **Task History**: Track execution history, failures, duration in admin interface
3. **Better Error Handling**: Automatic retries, detailed error logs, email notifications
4. **Environment Consistency**: Uses Django settings, no server-specific paths
5. **Email Notifications**: Built into application logic
6. **Easy Testing**: Can test and run manually from Django shell or admin
7. **Version Control**: Schedules can be created via migrations
8. **Monitoring**: Django admin provides detailed task monitoring dashboard

## Integration with Existing Projects

If you have an existing backup task (e.g., `core.tasks.backup`), you can migrate to this app:

1. Keep your existing function for backward compatibility
2. Add this app and configure it
3. Setup schedules using this app
4. Monitor for a few days
5. Remove old cron jobs or task schedulers

The app provides a `backup()` function for backward compatibility:

```python
from django_scheduled_backups.tasks import backup

# Simple backup without tracking or notifications
backup()
```

## Testing

Run the test suite:

```bash
pytest django_scheduled_backups/tests/
```

## License

This app is part of the School Menu project.

## Related Issue

This app was created to address [Issue #159](https://github.com/your-repo/issues/159) - Move DB backup from cron to Django-Q2.

## Version

1.0.0
