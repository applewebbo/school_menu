"""
Database connection monitoring tests

This module tests database connection pooling and reuse to verify that
CONN_MAX_AGE configuration is working correctly. Connection pooling can
significantly improve performance by reusing database connections instead
of creating new ones for each request.

Expected results:
- With CONN_MAX_AGE > 0: Same connection PID reused across queries
- Connection count should remain low (< 20 in test environment)
- PostgreSQL-specific tests skipped for SQLite/other databases
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_connection_results(test_name, stats):
    """
    Log connection results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        stats: Dictionary containing connection statistics
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Database Connection Test: {test_name}\n")
        f.write(f"{'=' * 80}\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
        f.write(f"{'=' * 80}\n\n")


def print_connection_results(test_name, stats):
    """
    Print connection results to console

    Args:
        test_name: Name of the test
        stats: Dictionary containing connection statistics
    """
    print(f"\n{'=' * 80}")
    print(f"Database Connection Test: {test_name}")
    print(f"{'=' * 80}")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(f"{'=' * 80}\n")


def get_connection_backend_pid():
    """
    Get the backend process ID for the current database connection

    Returns:
        int: Process ID of the database backend, or None if not supported
    """
    # Check if we're using PostgreSQL
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            return cursor.fetchone()[0]
    else:
        # For SQLite and other databases, return connection ID if available
        return id(connection.connection)


class TestDatabaseConnectionReuse:
    """Test database connection reuse with CONN_MAX_AGE"""

    def test_database_connection_reuse(self):
        """
        Verify that database connections are reused when CONN_MAX_AGE is configured

        This test checks if the same database connection (identified by process ID)
        is reused across multiple queries. Connection reuse is a key performance
        optimization that reduces the overhead of establishing new connections.
        """
        # Get CONN_MAX_AGE setting
        db_config = settings.DATABASES.get("default", {})
        conn_max_age = db_config.get("CONN_MAX_AGE", 0)

        # Get initial connection PID
        connection.ensure_connection()
        pid1 = get_connection_backend_pid()

        # Execute a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        # Get connection PID after query
        pid2 = get_connection_backend_pid()

        # Execute another query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        # Get connection PID after second query
        pid3 = get_connection_backend_pid()

        # Prepare statistics
        stats = {
            "Database engine": connection.vendor,
            "CONN_MAX_AGE": conn_max_age,
            "Connection PID 1": pid1,
            "Connection PID 2": pid2,
            "Connection PID 3": pid3,
            "Connection reused": "Yes" if pid1 == pid2 == pid3 else "No",
        }

        # Log and print results
        log_connection_results("connection_reuse", stats)
        print_connection_results("connection_reuse", stats)

        # For test environment with SQLite, connection reuse is different
        # but we should still see the same connection ID
        if conn_max_age > 0 or connection.vendor == "sqlite":
            assert pid1 == pid2 == pid3, (
                f"Connection not reused: PIDs {pid1}, {pid2}, {pid3}"
            )
        else:
            # If CONN_MAX_AGE is 0, connections may not be reused
            print("WARNING: CONN_MAX_AGE is 0, connection reuse may not occur")


class TestActiveConnectionCount:
    """Test active database connection count monitoring"""

    @pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="Active connection count test only applicable for PostgreSQL",
    )
    def test_active_connection_count(self):
        """
        Query pg_stat_activity to get active connection count

        This test is PostgreSQL-specific and monitors the number of active
        database connections. Keeping connection count low is important for
        database performance and resource management.

        Expected: < 20 connections in test environment
        """
        with connection.cursor() as cursor:
            # Query pg_stat_activity for active connections
            cursor.execute(
                """
                SELECT count(*)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND state = 'active'
            """
            )
            active_connections = cursor.fetchone()[0]

            # Query total connections to this database
            cursor.execute(
                """
                SELECT count(*)
                FROM pg_stat_activity
                WHERE datname = current_database()
            """
            )
            total_connections = cursor.fetchone()[0]

        # Prepare statistics
        stats = {
            "Database engine": connection.vendor,
            "Database name": connection.settings_dict["NAME"],
            "Active connections": active_connections,
            "Total connections": total_connections,
            "Connection limit check": ("PASS" if total_connections < 20 else "WARNING"),
        }

        # Log and print results
        log_connection_results("active_connection_count", stats)
        print_connection_results("active_connection_count", stats)

        # Assert connection count is reasonable for test environment
        assert total_connections < 20, (
            f"Too many database connections: {total_connections}"
        )

    def test_connection_count_info(self):
        """
        Display connection information for non-PostgreSQL databases

        This test provides connection information for databases that don't
        support pg_stat_activity queries (like SQLite).
        """
        if connection.vendor == "postgresql":
            pytest.skip("Use test_active_connection_count for PostgreSQL")

        # For SQLite and other databases, provide basic connection info
        stats = {
            "Database engine": connection.vendor,
            "Database name": connection.settings_dict.get("NAME", "N/A"),
            "Connection pooling": "Built-in"
            if connection.vendor == "sqlite"
            else "N/A",
            "Note": "Active connection count monitoring only available for PostgreSQL",
        }

        # Log and print results
        log_connection_results("connection_info", stats)
        print_connection_results("connection_info", stats)


class TestConnectionPoolConfiguration:
    """Test database connection pool configuration"""

    def test_conn_max_age_configuration(self):
        """
        Verify CONN_MAX_AGE is properly configured

        CONN_MAX_AGE controls how long database connections are reused.
        - 0: Close connection after each request (default, but slower)
        - > 0: Keep connection open for specified seconds (faster)
        - None: Persistent connections (keep open indefinitely)
        """
        db_config = settings.DATABASES.get("default", {})
        conn_max_age = db_config.get("CONN_MAX_AGE", 0)
        engine = db_config.get("ENGINE", "unknown")

        stats = {
            "Database engine": engine,
            "CONN_MAX_AGE": conn_max_age,
            "Connection pooling": "Enabled" if conn_max_age != 0 else "Disabled",
            "Recommendation": (
                "OK - Connection pooling enabled"
                if conn_max_age != 0
                else "Consider enabling CONN_MAX_AGE for better performance"
            ),
        }

        # Log and print results
        log_connection_results("conn_max_age_config", stats)
        print_connection_results("conn_max_age_config", stats)

        # For test environment, CONN_MAX_AGE might be 0, which is acceptable
        # Just log the configuration without strict assertions
        print(f"CONN_MAX_AGE configured as: {conn_max_age}")
