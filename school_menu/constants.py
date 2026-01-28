"""
Constants for school_menu application.

This module centralizes all magic numbers and constant values used throughout
the application for better maintainability and self-documenting code.
"""

# Cache timeouts (in seconds)
CACHE_TTL_24_HOURS = 86400  # 24 hours - default cache timeout for meals
CACHE_TTL_7_DAYS = 604800  # 7 days - cache timeout for annual meals

# CSV parsing
CSV_SAMPLE_SIZE = 1024  # Bytes to read for CSV format detection
CSV_HEADER_LINES = 5  # Number of lines to check for delimiter detection

# Week configuration
MIN_WEEK_NUMBER = 1  # Minimum week number in rotation
MAX_WEEK_NUMBER = 4  # Maximum week number in rotation
WEEKS_IN_ROTATION = 4  # Total number of weeks in menu rotation

# Season dates (equinoxes and solstices)
SPRING_EQUINOX_DAY = 21  # March 21st - start of spring
SPRING_EQUINOX_MONTH = 3  # March
AUTUMN_EQUINOX_DAY = 22  # September 22nd - end of summer
AUTUMN_EQUINOX_MONTH = 9  # September

# Winter months (October through February)
WINTER_MONTHS = [10, 11, 12, 1, 2]  # October, November, December, January, February

# Academic year
ACADEMIC_YEAR_START_MONTH = 9  # September - start of academic year

# Weekdays (Python datetime weekday() values)
WEEKDAY_MONDAY = 0
WEEKDAY_FRIDAY = 4
WEEKDAY_SATURDAY = 5
WEEKDAY_SUNDAY = 6

# Working days
FIRST_WORKING_DAY = WEEKDAY_MONDAY  # Monday
LAST_WORKING_DAY = WEEKDAY_FRIDAY  # Friday
FIRST_WEEKEND_DAY = WEEKDAY_SATURDAY  # Saturday

# Days in week
DAYS_IN_WEEK = 7
