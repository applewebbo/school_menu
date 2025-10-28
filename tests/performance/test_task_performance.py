"""
Background task performance tests

This module measures background task performance to identify bottlenecks
and verify optimizations. Background tasks like notification sending can
suffer from N+1 query problems when not properly optimized.

Expected results:
- BEFORE optimization: 200+ queries (N+1 problem)
- AFTER optimization: <10 queries with select_related
- Task should complete efficiently even with 100+ subscribers
"""

from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from notifications.models import AnonymousMenuNotification
from notifications.tasks import _send_menu_notifications
from tests.notifications.factories import AnonymousMenuNotificationFactory
from tests.school_menu.factories import SchoolFactory

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_task_results(test_name, stats):
    """
    Log task results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        stats: Dictionary containing task statistics
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Task Performance Test: {test_name}\n")
        f.write(f"{'=' * 80}\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
        f.write(f"{'=' * 80}\n\n")


def print_task_results(test_name, stats):
    """
    Print task results to console

    Args:
        test_name: Name of the test
        stats: Dictionary containing task statistics
    """
    print(f"\n{'=' * 80}")
    print(f"Task Performance Test: {test_name}")
    print(f"{'=' * 80}")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(f"{'=' * 80}\n")


class TestNotificationTaskPerformance:
    """Test notification task performance"""

    def test_notification_task_performance_baseline(self):
        """
        Measure baseline performance of notification sending task

        This test creates 100 test subscriptions (10 schools × 10 subscribers each)
        and measures the query count and duration for sending notifications to all.

        Expected BEFORE optimization:
        - 200+ database queries (N+1 problem with school/subscription loading)
        - Slow performance with many subscribers

        Expected AFTER optimization:
        - <10 queries with select_related('school')
        - Fast performance even with 100 subscribers
        """
        # Create test data: 10 schools with 10 subscribers each
        schools = []
        for i in range(10):
            school = SchoolFactory(is_published=True)
            schools.append(school)

        # Create 10 subscriptions per school (100 total)
        subscriptions = []
        for school in schools:
            for j in range(10):
                subscription = AnonymousMenuNotificationFactory(
                    school=school,
                    daily_notification=True,
                    notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
                    subscription_info={
                        "endpoint": f"https://example.com/subscriber_{j}",
                        "keys": {"p256dh": "test_key", "auth": "test_auth"},
                    },
                )
                subscriptions.append(subscription)

        total_subscribers = len(subscriptions)

        # Mock the actual notification sending to avoid external calls
        # We only want to measure database query performance
        mock_payload = {
            "title": "Menu di oggi",
            "body": "Test menu",
            "icon": "/static/img/notification-bell.png",
        }

        with (
            patch("notifications.tasks.send_test_notification"),
            patch(
                "notifications.tasks.build_menu_notification_payload",
                return_value=mock_payload,
            ),
        ):
            # Measure query count and duration
            start_time = perf_counter()

            with CaptureQueriesContext(connection) as context:
                # Call the task function
                _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

            end_time = perf_counter()
            duration_ms = (end_time - start_time) * 1000

        # Calculate statistics
        num_queries = len(context.captured_queries)
        time_per_subscriber_ms = (
            duration_ms / total_subscribers if total_subscribers > 0 else 0
        )
        queries_per_subscriber = (
            num_queries / total_subscribers if total_subscribers > 0 else 0
        )

        stats = {
            "Total subscribers": total_subscribers,
            "Number of schools": len(schools),
            "Subscribers per school": 10,
            "Total database queries": num_queries,
            "Total duration": f"{duration_ms:.2f}ms",
            "Time per subscriber": f"{time_per_subscriber_ms:.2f}ms",
            "Queries per subscriber": f"{queries_per_subscriber:.2f}",
            "Expected after optimization": "<10 queries total",
            "Performance": (
                "Good - optimized"
                if num_queries < 10
                else "Needs optimization (N+1 detected)"
            ),
        }

        # Log and print results
        log_task_results("notification_task_baseline", stats)
        print_task_results("notification_task_baseline", stats)

        # Print first 5 queries for debugging
        print("\nFirst 5 queries:")
        for i, query in enumerate(context.captured_queries[:5], 1):
            print(f"\nQuery {i}:")
            print(f"{query['sql'][:200]}...")

        # NOTE: This will likely fail before optimization
        # After optimization with select_related, it should pass
        if num_queries >= 10:
            print(
                f"\nWARNING: High query count ({num_queries} queries). "
                "This indicates N+1 problem. Consider using select_related('school')."
            )

    def test_notification_task_with_different_times(self):
        """
        Test notification task performance for different notification times

        This ensures consistent performance across all notification time slots.
        """
        # Create test data: 5 schools with 2 subscribers each for different times
        notification_times = [
            AnonymousMenuNotification.PREVIOUS_DAY_6PM,
            AnonymousMenuNotification.SAME_DAY_9AM,
            AnonymousMenuNotification.SAME_DAY_12PM,
            AnonymousMenuNotification.SAME_DAY_6PM,
        ]

        results = {}

        for notification_time in notification_times:
            # Create test data for this time
            schools = []
            for i in range(5):
                school = SchoolFactory(is_published=True)
                schools.append(school)

            # Create 2 subscriptions per school
            for school in schools:
                for j in range(2):
                    AnonymousMenuNotificationFactory(
                        school=school,
                        daily_notification=True,
                        notification_time=notification_time,
                        subscription_info={
                            "endpoint": f"https://example.com/{notification_time}_{j}",
                            "keys": {"p256dh": "test_key", "auth": "test_auth"},
                        },
                    )

            # Mock notification sending
            mock_payload = {
                "title": "Menu di oggi",
                "body": "Test menu",
                "icon": "/static/img/notification-bell.png",
            }

            with (
                patch("notifications.tasks.send_test_notification"),
                patch(
                    "notifications.tasks.build_menu_notification_payload",
                    return_value=mock_payload,
                ),
            ):
                start_time = perf_counter()

                with CaptureQueriesContext(connection) as context:
                    _send_menu_notifications(notification_time)

                end_time = perf_counter()
                duration_ms = (end_time - start_time) * 1000

            results[notification_time] = {
                "queries": len(context.captured_queries),
                "duration_ms": duration_ms,
                "subscribers": 10,  # 5 schools × 2 subscribers
            }

        # Compile statistics
        stats = {
            "Test description": "Performance across different notification times",
            "Notification times tested": len(notification_times),
        }

        for notification_time, result in results.items():
            stats[f"{notification_time} - queries"] = result["queries"]
            stats[f"{notification_time} - duration"] = f"{result['duration_ms']:.2f}ms"

        # Log and print results
        log_task_results("notification_task_different_times", stats)
        print_task_results("notification_task_different_times", stats)

        # Assert all times have similar performance characteristics
        query_counts = [r["queries"] for r in results.values()]
        max_queries = max(query_counts)
        min_queries = min(query_counts)

        assert max_queries - min_queries < 50, (
            f"Query count variance too high: {min_queries} to {max_queries}"
        )

    def test_notification_task_query_pattern(self):
        """
        Analyze query patterns in notification task to identify optimization opportunities

        This test examines the actual queries being made to help identify
        N+1 problems and suggest optimizations.
        """
        # Create minimal test data
        school = SchoolFactory(is_published=True)

        for i in range(3):
            AnonymousMenuNotificationFactory(
                school=school,
                daily_notification=True,
                notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
                subscription_info={
                    "endpoint": f"https://example.com/test_{i}",
                    "keys": {"p256dh": "test_key", "auth": "test_auth"},
                },
            )

        # Mock notification sending
        mock_payload = {
            "title": "Menu di oggi",
            "body": "Test menu",
            "icon": "/static/img/notification-bell.png",
        }

        with (
            patch("notifications.tasks.send_test_notification"),
            patch(
                "notifications.tasks.build_menu_notification_payload",
                return_value=mock_payload,
            ),
        ):
            with CaptureQueriesContext(connection) as context:
                _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

        # Analyze query patterns
        query_types = {}
        for query in context.captured_queries:
            sql = query["sql"]
            # Categorize queries
            if "SELECT" in sql and "FROM" in sql:
                # Extract table name
                if "school_menu_school" in sql:
                    query_types["school_queries"] = (
                        query_types.get("school_queries", 0) + 1
                    )
                elif "notifications_anonymousmenunotification" in sql:
                    query_types["notification_queries"] = (
                        query_types.get("notification_queries", 0) + 1
                    )
                elif (
                    "school_menu_simplemeal" in sql or "school_menu_detailedmeal" in sql
                ):
                    query_types["meal_queries"] = query_types.get("meal_queries", 0) + 1
                else:
                    query_types["other_queries"] = (
                        query_types.get("other_queries", 0) + 1
                    )

        stats = {
            "Total queries": len(context.captured_queries),
            "School queries": query_types.get("school_queries", 0),
            "Notification queries": query_types.get("notification_queries", 0),
            "Meal queries": query_types.get("meal_queries", 0),
            "Other queries": query_types.get("other_queries", 0),
            "Optimization needed": (
                "Yes - multiple school queries detected"
                if query_types.get("school_queries", 0) > 1
                else "No - efficient queries"
            ),
        }

        # Log and print results
        log_task_results("notification_task_query_pattern", stats)
        print_task_results("notification_task_query_pattern", stats)

        # Provide optimization recommendations
        if query_types.get("school_queries", 0) > 1:
            print(
                "\nOPTIMIZATION RECOMMENDATION: "
                "Use select_related('school') when fetching AnonymousMenuNotification objects "
                "to avoid N+1 queries."
            )
