# Welcome to Mensa Scuola

Do you want to know what your kid is eating at school. Sick of searching through a long excel file published on the school site or making complex operations to calculate what week are you in?

So do I... so I created this little project to automate the process. You can create an account, a school, upload the menu in csv format or add it manually via a form. You can have simple, detailed or annual meals. You can share the menu with other parents and get feedback on the menu. I'm now working on push notifications for getting a daily reminder of what your kid will it in the current day if you subscribe to the service. You can check the instructions on the site at this link https://menu.webbografico.com/help (only in italian, working on getting the site traslated in a future update). All the site is GPDR compliant and you can delete your account at any time.

Feel free to use it for your kids

Made with **Django**, **Tailwind** and **Htmx**

Demo Site:
http://menu.webbografico.com

## Technical Setup

### Cache Configuration

The application uses a multi-tier caching strategy to improve performance:

**Local Development:**
- Uses database cache (SQLite-based)
- No external dependencies required
- Automatically configured via Django's cache table

**Production:**
- Uses Redis as primary cache backend
- Database cache as fallback for resilience
- Configured via environment variables

**Testing:**
- Uses dummy cache (no actual caching)
- Prevents test pollution and improves test performance

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
   - `get_cached_or_query()` - Generic cache-or-query helper (24h TTL default)
   - `invalidate_school_meals()` - Clear meal caches for a school
   - Pattern-based invalidation works only with Redis backend

**Note:** The cache configuration follows the same pattern as Django Q_CLUSTER, using database backend for local development and Redis for production.
