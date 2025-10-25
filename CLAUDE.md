# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Mensa Scuola" is a Django web application that helps parents track school menus for their children. Users can create accounts, manage schools, upload menus in CSV format, and receive daily notifications about meals. The application is built with Django, Tailwind CSS (using DaisyUI), and htmx for SPA-like features.

## Development Commands

This project uses `just` (justfile) and `uv` for task management and dependency handling.

### Setup
- `just install` - Install/sync dependencies using uv
- `just update_all` - Update all dependencies and pre-commit hooks
- `just update <package>` - Update a specific package
- `just lock` - Rebuild the lock file from scratch
- `just clean` - Remove temporary files (.venv, .pytest_cache, etc.)
- `just fresh` - Recreate the entire virtualenv from scratch

### Development Server
- `just local` - Run local development server with Tailwind (single process)
- `just serve` - Run development server + workers using overmind (requires overmind)
  - Starts both web server and Django Q2 task worker
  - Uses Procfile.dev configuration

### Database
- `just makemigrations` - Create database migrations
- `just migrate` - Run database migrations

### Internationalization
- `just makemessages` - Update translation files
- `just compilemessages` - Compile translation files

### Background Tasks
- `just tasks` - Run Django Q2 task worker manually

### Testing & Quality
- `just test [args]` - Run tests sequentially with pytest (useful for debugging, -s flag for print statements, -x to stop on first failure)
- `just ftest [args]` - Run tests in parallel using 8 workers (faster, for CI/pre-commit)
- `just lint` - Run Ruff linting/formatting and all pre-commit hooks
- `just secure` - Check for unsecured dependencies

### Environment Configuration
The project uses `ENVIRONMENT` env var to control settings:
- `ENVIRONMENT=dev` - Development (SQLite, DEBUG=True)
- `ENVIRONMENT=prod` - Production (PostgreSQL, DEBUG=False)
- `ENVIRONMENT=test` - Testing (in-memory SQLite, logging disabled)

All commands prefix with `uv run` to execute in the project's virtual environment.

## High-Level Architecture

### Apps Structure
The project is organized into multiple Django apps:

- **core** - Project settings, main URL configuration, WSGI/ASGI
- **school_menu** - Core business logic for schools and menus (main app)
- **users** - Custom user model (email-based authentication, no username)
- **notifications** - Push notification system for daily menu reminders
- **contacts** - Contact form functionality
- **templates/** - All templates are stored at project root, not in individual apps

### Menu System Architecture

The application supports three distinct menu types through Django model inheritance:

1. **DetailedMeal** - Full menu breakdown (first course, second course, side dish, fruit, snack)
2. **SimpleMeal** - Text-based menu with morning/afternoon snacks
3. **AnnualMeal** - Date-specific menus with activation status

All inherit from abstract `Meal` model which provides:
- Week rotation (1-4 weeks)
- Day of week (Monday-Friday)
- Season (summer/winter)
- Type (Standard, Gluten-free, Lactose-free, Vegetarian, Special)

**Key Logic (school_menu/utils.py):**
- `calculate_week()` - Maps ISO week to 1-4 rotation with configurable bias
- `get_season()` - Auto-determines season or uses school setting
- `get_meals()` - Retrieves weekly/daily meals based on school configuration
- `build_types_menu()` - Builds available alternate menus based on school settings

### School Configuration

Each `School` model has:
- One-to-one relationship with User
- Academic year boundaries (start/end day/month)
- Menu type selection (Simple/Detailed/Annual)
- Alternative menu flags (no_gluten, no_lactose, vegetarian, special)
- Week bias for rotation adjustment
- Auto-generated slug from name+city
- Season choice (PRIMAVERILE/INVERNALE/AUTOMATICA)

### Authentication & Users

Uses **django-allauth** with custom configuration:
- Email-only authentication (no username)
- Custom signup/login forms (users/forms.py)
- Mandatory email verification
- Terms & conditions agreement field on User model
- Custom UserManager (users/managers.py)

### Notification System

**Django Q2** task queue (backed by Redis):
- **AnonymousMenuNotification** - Stores web push subscriptions with notification preferences
- **DailyNotification** - Tracks notification events
- Configurable notification times (previous day 6pm, same day 9am/12pm/6pm)
- Uses django-webpush for browser push notifications
- Scheduled tasks run through Q cluster workers

### Frontend Stack

- **Tailwind CSS** via django-tailwind-cli with DaisyUI components
- **htmx** for dynamic interactions (django-htmx integration)
- **Alpine.js** for frontend interactivity
- **django-template-partials** for component-based templates
- **heroicons** for icons
- **PWA support** via django-pwa (offline capability, installable)

### Import/Export System

Uses **django-import-export** with custom validation:
- CSV uploads for menu data
- `validate_dataset()` - Validates weekly menu format
- `validate_annual_dataset()` - Validates annual menu format
- `ChoicesWidget` - Maps display values to database choices during import

## Coding Standards

### Python & Django
- Follow PEP 8 with 120 character line limit
- Use double quotes for strings
- Use f-strings for formatting
- Sort imports with isort (handled by Ruff)
- Prefer function-based views over class-based views
- Use `get_object_or_404` instead of manual exception handling
- Use `select_related` and `prefetch_related` to avoid N+1 queries

### Models
- Add `__str__` methods to all models
- Use `related_name` for foreign keys
- Define `Meta` class with ordering, verbose_name
- Use `blank=True` for optional form fields, `null=True` for optional DB fields
- Use singular nouns for model names (e.g., `School` not `Schools`)

### Views & URLs
- Always validate and sanitize user input
- Handle exceptions gracefully with try/except blocks
- Implement proper pagination for list views
- Use descriptive URL names for reverse lookups
- Always end URL patterns with trailing slash

### Templates
- Store all templates in project-level `templates/` directory (NOT in app directories)
- Use template inheritance with base templates
- Use kebab-case for template file names (e.g., `my-template.html`)
- Avoid complex logic in templates - use template tags or move to views
- Implement CSRF protection in all forms
- Use crispy forms with Tailwind pack for rendering

### Forms
- Use ModelForms when working with model instances
- Use crispy forms (crispy_tailwind) for better rendering

### Testing
- Always write unit tests for new features and ensure they pass
- Use pytest, pytest-django, and django-test-plus
- Put all tests in root-level `tests/` directory
- Use `pytestmark = pytest.mark.django_db` for tests needing DB access
- Test both positive and negative scenarios
- Use consistent naming: `test_*.py` for files
- Don't test Django internals, only project-specific logic
- Coverage requirement: 100% (enforced via pytest.ini)
- Use fixtures from factory-boy (pytest-factoryboy) for test data

### Code Quality Tools
Pre-commit hooks run automatically via `.pre-commit-config.yaml`:
- **pyupgrade** - Upgrades to Python 3.13+ syntax
- **django-upgrade** - Upgrades to Django 5.2 patterns
- **djade** - Django template linting
- **Ruff** - Linting and formatting (replaces flake8, isort, black)
- **bandit** - Security linting
- **rustywind** - Tailwind CSS class ordering

## Database

- Development: SQLite (db.sqlite3)
- Production: PostgreSQL
- Testing: In-memory SQLite
- Use migrations for ALL database changes
- Optimize queries with select_related/prefetch_related
- Avoid N+1 query problems

## Additional Configuration

- **django-environ** - Manages environment variables from .env file
- **django-anymail** with Mailgun - Email backend
- **django-dbbackup** - Database backups to Dropbox
- **django-cookiebanner** - GDPR cookie consent
- **django-social-share** - Social sharing functionality
- **Whitenoise** - Static file serving
- **django-debug-toolbar** - Development debugging (only in dev mode)

## Important Settings

- Locale: Italian (it-IT), timezone: Europe/Rome
- Translation enabled (USE_I18N = True)
- Static files: `static/` (source) → `staticfiles/` (collected)
- Media files: `media/`
- Custom setting: `ENABLE_SCHOOL_DATE_CHECK` - Controls school date validation

## Naming Conventions

- kebab-case: template files (`my-template.html`)
- snake_case: functions, variables (`my_function`, `my_variable`)
- PascalCase: model/class names (`MyModel`)
- UPPERCASE: constants (`MY_CONSTANT`)
- Singular: model names (`Book` not `Books`)
- Plural: model managers (`BooksManager`)
- Descriptive names: `calculate_total_price` not `calc_price`

## Documentation

Use docstrings for all public functions, classes, and methods.
