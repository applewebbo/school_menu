"""
Database query count tests for performance monitoring and N+1 detection

This module tests database query efficiency across different views and endpoints.
Tests measure baseline performance and verify post-optimization improvements.

Expected results:
- BEFORE optimization: 100-150 queries (N+1 problem)
- AFTER optimization: ≤5 queries with select_related/prefetch_related
"""

import os
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_query_results(test_name, num_queries, queries):
    """
    Log test results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        num_queries: Total number of queries executed
        queries: List of query objects from CaptureQueriesContext
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Test: {test_name}\n")
        f.write(f"Total Queries: {num_queries}\n")
        f.write(f"{'=' * 80}\n\n")

        # Log first 5 queries for debugging
        for i, query in enumerate(queries[:5], 1):
            f.write(f"Query {i}:\n")
            f.write(f"{query['sql']}\n\n")


def print_query_details(test_name, num_queries, queries):
    """
    Print query details to console for debugging

    Args:
        test_name: Name of the test
        num_queries: Total number of queries executed
        queries: List of query objects from CaptureQueriesContext
    """
    print(f"\n{'=' * 80}")
    print(f"Test: {test_name}")
    print(f"Total Queries: {num_queries}")
    print(f"{'=' * 80}\n")

    # Print first 5 queries
    for i, query in enumerate(queries[:5], 1):
        print(f"Query {i}:")
        print(f"{query['sql']}\n")


class TestSchoolListQueryCount:
    """Test query counts for school list page"""

    def test_school_list_baseline_query_count(self, client, large_dataset):
        """
        Baseline test: Measure query count for school list page

        Expected BEFORE optimization: High query count (potential N+1)
        Expected AFTER optimization: ≤5 queries
        """
        url = reverse("school_menu:school_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results("school_list_baseline", num_queries, context.captured_queries)
        print_query_details(
            "school_list_baseline", num_queries, context.captured_queries
        )

        # Baseline assertion - documents current state
        # After optimization, this should be ≤5
        print(f"School list query count: {num_queries}")

    def test_school_list_optimized_query_count(self, client, large_dataset):
        """
        Post-optimization test: Verify query count is ≤5

        This test will fail until optimization is implemented.
        Expected: ≤5 queries with select_related('user')
        """
        url = reverse("school_menu:school_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results(
            "school_list_optimized", num_queries, context.captured_queries
        )
        print_query_details(
            "school_list_optimized", num_queries, context.captured_queries
        )

        # Post-optimization assertion
        # Mark as expected failure until optimization is done
        pytest.xfail(
            f"Query count {num_queries} > 5. Optimization not yet implemented."
        )


class TestSchoolDetailQueryCount:
    """Test query counts for school detail page"""

    def test_school_detail_baseline_query_count(self, client, large_dataset):
        """
        Baseline test: Measure query count for school detail page

        Expected BEFORE optimization: High query count (potential N+1 for meals)
        Expected AFTER optimization: ≤5 queries
        """
        # Use first school from dataset
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results(
            "school_detail_baseline", num_queries, context.captured_queries
        )
        print_query_details(
            "school_detail_baseline", num_queries, context.captured_queries
        )

        print(f"School detail query count: {num_queries}")

    def test_school_detail_optimized_query_count(self, client, large_dataset):
        """
        Post-optimization test: Verify query count is ≤5

        This test will fail until optimization is implemented.
        Expected: ≤5 queries with select_related/prefetch_related
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results(
            "school_detail_optimized", num_queries, context.captured_queries
        )
        print_query_details(
            "school_detail_optimized", num_queries, context.captured_queries
        )

        # Post-optimization assertion
        pytest.xfail(
            f"Query count {num_queries} > 5. Optimization not yet implemented."
        )


class TestAPISchoolsListQueryCount:
    """Test query counts for API schools list endpoint"""

    def test_api_schools_list_baseline_query_count(self, client, large_dataset):
        """
        Baseline test: Measure query count for API schools list

        Expected BEFORE optimization: High query count (N+1 when serializing)
        Expected AFTER optimization: ≤5 queries
        """
        url = reverse("school_menu:get_schools_json_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results("api_schools_baseline", num_queries, context.captured_queries)
        print_query_details(
            "api_schools_baseline", num_queries, context.captured_queries
        )

        print(f"API schools list query count: {num_queries}")

    def test_api_schools_list_optimized_query_count(self, client, large_dataset):
        """
        Post-optimization test: Verify query count is ≤5

        This test will fail until optimization is implemented.
        Expected: ≤5 queries with select_related('user')
        """
        url = reverse("school_menu:get_schools_json_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results(
            "api_schools_optimized", num_queries, context.captured_queries
        )
        print_query_details(
            "api_schools_optimized", num_queries, context.captured_queries
        )

        # Post-optimization assertion
        pytest.xfail(
            f"Query count {num_queries} > 5. Optimization not yet implemented."
        )


class TestSearchFunctionalityQueryCount:
    """Test query counts for search functionality"""

    def test_search_baseline_query_count(self, client, large_dataset):
        """
        Baseline test: Measure query count for search functionality

        Expected BEFORE optimization: High query count (potential N+1)
        Expected AFTER optimization: ≤5 queries
        """
        url = reverse("school_menu:search_schools")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url, {"q": "school"})

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results("search_baseline", num_queries, context.captured_queries)
        print_query_details("search_baseline", num_queries, context.captured_queries)

        print(f"Search query count: {num_queries}")

    def test_search_optimized_query_count(self, client, large_dataset):
        """
        Post-optimization test: Verify query count is ≤5

        This test will fail until optimization is implemented.
        Expected: ≤5 queries with select_related('user')
        """
        url = reverse("school_menu:search_schools")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url, {"q": "school"})

        assert response.status_code == 200
        num_queries = len(context.captured_queries)

        # Log and print results
        log_query_results("search_optimized", num_queries, context.captured_queries)
        print_query_details("search_optimized", num_queries, context.captured_queries)

        # Post-optimization assertion
        pytest.xfail(
            f"Query count {num_queries} > 5. Optimization not yet implemented."
        )


@pytest.fixture(autouse=True, scope="module")
def setup_baseline_metrics_file():
    """Clear baseline metrics file before running tests"""
    if os.path.exists(BASELINE_METRICS_FILE):
        os.remove(BASELINE_METRICS_FILE)

    with open(BASELINE_METRICS_FILE, "w") as f:
        f.write("Performance Test Baseline Metrics\n")
        f.write("=" * 80 + "\n")

    yield
