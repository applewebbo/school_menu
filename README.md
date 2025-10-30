# Welcome to Mensa Scuola

Do you want to know what your kid is eating at school. Sick of searching through a long excel file published on the school site or making complex operations to calculate what week are you in?

So do I... so I created this little project to automate the process. You can create an account, a school, upload the menu in csv format or add it manually via a form. You can have simple, detailed or annual meals. You can share the menu with other parents and get feedback on the menu. I'm now working on push notifications for getting a daily reminder of what your kid will it in the current day if you subscribe to the service. You can check the instructions on the site at this link https://menu.webbografico.com/help (only in italian, working on getting the site traslated in a future update). All the site is GPDR compliant and you can delete your account at any time.

Feel free to use it for your kids

Made with **Django**, **Tailwind** and **Htmx**

Demo Site:
http://menu.webbografico.com

## Setup Instructions

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Redis (optional, for production caching and background tasks)

### Installation

1. **Install dependencies:**
   ```bash
   just install
   ```

2. **Run database migrations:**
   ```bash
   just migrate
   ```

3. **Create cache table:**
   ```bash
   uv run python manage.py createcachetable django_cache
   ```

4. **Compile translation files:**
   ```bash
   just compilemessages
   ```

5. **Run the development server:**
   ```bash
   just local
   ```

### Environment Configuration

Create a `.env` file in the project root:

```env
ENVIRONMENT=dev  # Options: dev, prod, test
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Production only
DATABASE_URL=postgres://user:pass@localhost/dbname
REDIS_PASSWORD=your-redis-password
```

## Just Commands

This project uses [just](https://github.com/casey/just) for task management. Available commands:

### Setup
- `just install` - Install/sync dependencies using uv
- `just update_all` - Update all dependencies and pre-commit hooks
- `just update <package>` - Update a specific package
- `just lock` - Rebuild lock file from scratch
- `just clean` - Remove temporary files (.venv, .pytest_cache, etc.)
- `just fresh` - Recreate virtualenv from scratch (clean + install)

### Development
- `just local` - Run local development server with Tailwind
- `just serve` - Run development server + workers using overmind
- `just makemigrations` - Create database migrations
- `just migrate` - Run database migrations
- `just compilemessages` - Compile translation files
- `just makemessages` - Update translation files
- `just tasks` - Run Django Q2 task worker

### Testing & Quality
- `just test [args]` - Run tests sequentially (useful for debugging with -s, -x flags)
- `just ftest [args]` - Run tests in parallel using 8 workers (faster, for CI)
- `just perftest [args]` - Run performance tests only
- `just perfbaseline` - Run complete performance baseline suite
- `just lint` - Run Ruff linting/formatting and pre-commit hooks
- `just secure` - Check for unsecured dependencies

## Code Stack

### Backend
- **Django 5.0+** - Web framework
- **Django Q2** - Background task queue with Redis
- **Django REST Framework** - API endpoints
- **PostgreSQL** - Production database
- **SQLite** - Development/testing database
- **Redis** - Caching and task queue backend

### Frontend
- **Tailwind CSS** - Utility-first CSS framework (via django-tailwind-cli)
- **DaisyUI** - Tailwind component library
- **htmx** - Dynamic HTML without JavaScript
- **Alpine.js** - Lightweight JavaScript framework
- **Heroicons** - Icon library

### Authentication & User Management
- **django-allauth** - Email-based authentication with social login support
- **django-crispy-forms** + **crispy-tailwind** - Form rendering

### Features & Utilities
- **django-import-export** - CSV/Excel import/export for menus
- **django-pwa** - Progressive Web App support
- **django-webpush** - Browser push notifications
- **django-dbbackup** - Database backups to Dropbox
- **django-cookiebanner** - GDPR cookie consent
- **django-social-share** - Social sharing functionality
- **Whitenoise** - Static file serving

### Development Tools
- **uv** - Fast Python package manager
- **pytest** + **pytest-django** - Testing framework
- **factory-boy** - Test data generation
- **Ruff** - Linting and formatting
- **pre-commit** - Git hooks for code quality
- **django-debug-toolbar** - Development debugging (dev only)
- **Locust** - Performance testing
- **pytest-benchmark** - Performance benchmarking

## Technical Setup

### Cache Configuration

The application uses a comprehensive multi-tier caching strategy with automatic invalidation to improve performance:

**Local Development:**
- Uses database cache (SQLite-based)
- No external dependencies required
- Automatically configured via Django's cache table

**Production:**
- Uses Redis as primary cache backend
- Database cache as fallback for resilience
- Configured via environment variables
- Expected cache hit rate: >98% for public pages
- Query reduction: 60-65% overall, 95-96% for meal queries

**Testing:**
- Uses dummy cache (no actual caching)
- Prevents test pollution and improves test performance

#### Cache Strategy

The application implements a hybrid cache invalidation approach:

1. **Automatic Model-Level Invalidation:**
   - `SimpleMeal`, `DetailedMeal`, `AnnualMeal` models override `save()` and `delete()` methods
   - School model invalidates all related caches when settings change
   - Ensures cache consistency without manual intervention

2. **Query-Level Caching:**
   - Individual meal queries cached via `get_meals()` and `get_meals_for_annual_menu()`
   - Cache keys include school_id, week, season, and meal_type for isolation
   - TTL: 24 hours for regular meals, 7 days for annual menus

3. **View-Level Caching:**
   - JSON API endpoint uses `@cache_page` decorator (24h TTL)
   - Automatically invalidated when meals change

4. **Database Indexes:**
   - `SimpleMeal`: (school, week, season)
   - `DetailedMeal`: (school, week, season)
   - `AnnualMeal`: (school, date, is_active)
   - Optimizes cache misses and cold-start performance

#### Setup Instructions

1. **Create cache table** (required for local dev and production fallback):
   ```bash
   python manage.py createcachetable django_cache
   ```

2. **Production Redis** (optional, only for production):
   - Redis is automatically configured if available
   - Set `REDIS_PASSWORD` environment variable if needed
   - Uses the same Redis instance as Django Q2 task queue (db 1 for cache, db 0 for tasks)

3. **Cache utilities** are available in `school_menu/cache.py`:
   - `get_meal_cache_key()` - Generate cache keys for meals
   - `get_cached_or_query()` - Generic cache-or-query helper with logging
   - `invalidate_meal_cache()` - Clear all meal-related caches for a school
   - `invalidate_school_cache()` - Clear ALL caches for a school
   - Pattern-based invalidation works only with Redis backend

#### Management Commands

The application provides management commands for cache operations:

```bash
# Display cache statistics (Redis only)
python manage.py cache_stats

# Clear all cache
python manage.py clear_cache --all

# Clear cache for specific school by ID
python manage.py clear_cache --school 1

# Clear cache for specific school by slug
python manage.py clear_cache --slug my-school-city

# Warm up cache for all published schools
python manage.py warm_cache

# Warm up cache for specific school
python manage.py warm_cache --school 1
```

#### Cache Timeouts (TTL)

Configured in `settings.CACHE_TIMEOUTS`:

- **MEAL**: 86400 seconds (24 hours) - Regular meal data changes infrequently
- **ANNUAL_MEAL**: 604800 seconds (7 days) - Annual menus are more stable
- **TYPES_MENU**: 86400 seconds (24 hours) - Alternative menu availability
- **JSON_API**: 86400 seconds (24 hours) - Public JSON API responses
- **SCHOOL_PAGE**: 86400 seconds (24 hours) - Public school menu pages

#### Troubleshooting

**Cache not clearing after meal updates:**
- Verify model `save()` methods are being called (bulk operations may bypass them)
- Run `python manage.py clear_cache --school <id>` to manually clear
- Check Redis connection: `python manage.py cache_stats`

**High memory usage:**
- Run `python manage.py cache_stats` to check key counts
- Consider reducing TTL values in `CACHE_TIMEOUTS`
- Run `python manage.py clear_cache --all` to reset

**Stale data after CSV import:**
- CSV imports explicitly call `invalidate_meal_cache()` after bulk operations
- If data still stale, manually clear: `python manage.py clear_cache --school <id>`

**Cache logging:**
- Set Django logging level to DEBUG to see cache hit/miss logs
- Logs include cache key, operation type (HIT/MISS/SET), and TTL

**Note:** The cache configuration follows the same pattern as Django Q_CLUSTER, using database backend for local development and Redis for production.
