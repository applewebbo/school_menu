"""
Duplicate query detection tests for identifying N+1 query problems

This module detects duplicate SQL queries which are a strong indicator of N+1 problems.
Duplicate queries typically occur when accessing related objects in a loop without
using select_related or prefetch_related.

Example N+1 pattern:
    schools = School.objects.all()  # 1 query
    for school in schools:
        print(school.user.email)  # N additional queries (one per school)

Expected results:
- BEFORE optimization: Many duplicate queries detected
- AFTER optimization: No duplicate queries (or minimal duplicates for legitimate reasons)
"""

from collections import Counter

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.performance]


def analyze_duplicate_queries(queries):
    """
    Analyze queries to detect duplicates (N+1 indicator)

    Args:
        queries: List of query objects from CaptureQueriesContext

    Returns:
        dict: Contains duplicate query analysis
    """
    # Extract just the SQL (without parameters) for comparison
    sql_statements = [query["sql"] for query in queries]

    # Count occurrences of each query
    query_counts = Counter(sql_statements)

    # Find duplicates (queries that appear more than once)
    duplicates = {sql: count for sql, count in query_counts.items() if count > 1}

    return {
        "total_queries": len(queries),
        "unique_queries": len(query_counts),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
    }


def print_duplicate_analysis(test_name, analysis):
    """
    Print duplicate query analysis to console

    Args:
        test_name: Name of the test
        analysis: Analysis dict from analyze_duplicate_queries
    """
    print(f"\n{'=' * 80}")
    print(f"Duplicate Query Analysis: {test_name}")
    print(f"{'=' * 80}")
    print(f"Total queries: {analysis['total_queries']}")
    print(f"Unique queries: {analysis['unique_queries']}")
    print(f"Duplicate query patterns: {analysis['duplicate_count']}\n")

    if analysis["duplicates"]:
        print("Duplicate Queries Detected (N+1 indicators):")
        print("-" * 80)
        for sql, count in analysis["duplicates"].items():
            print(f"\nExecuted {count} times:")
            print(f"{sql[:200]}...")  # Print first 200 chars
    else:
        print("No duplicate queries detected!")

    print(f"{'=' * 80}\n")


class TestDuplicateQueriesDetection:
    """Detect duplicate queries across different views"""

    def test_school_list_duplicate_queries(self, client, large_dataset):
        """
        Detect duplicate queries in school list page

        N+1 pattern example:
        - Query 1: SELECT * FROM school WHERE is_published=True
        - Query 2-101: SELECT * FROM user WHERE id=? (repeated for each school)
        """
        url = reverse("school_menu:school_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200

        # Analyze for duplicates
        analysis = analyze_duplicate_queries(context.captured_queries)
        print_duplicate_analysis("school_list", analysis)

        # Report findings
        if analysis["duplicate_count"] > 0:
            print(
                f"WARNING: Found {analysis['duplicate_count']} duplicate query patterns"
            )
            print("This suggests N+1 query problems that should be optimized")

    def test_school_detail_duplicate_queries(self, client, large_dataset):
        """
        Detect duplicate queries in school detail page

        N+1 pattern example:
        - Query 1: SELECT * FROM school WHERE slug=?
        - Query 2-61: SELECT * FROM meal WHERE school_id=? AND week=? AND day=?
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200

        # Analyze for duplicates
        analysis = analyze_duplicate_queries(context.captured_queries)
        print_duplicate_analysis("school_detail", analysis)

        # Report findings
        if analysis["duplicate_count"] > 0:
            print(
                f"WARNING: Found {analysis['duplicate_count']} duplicate query patterns"
            )
            print("This suggests N+1 query problems that should be optimized")

    def test_api_schools_duplicate_queries(self, client, large_dataset):
        """
        Detect duplicate queries in API schools list endpoint

        N+1 pattern example:
        - Query 1: SELECT * FROM school WHERE is_published=True
        - Query 2-101: SELECT * FROM user WHERE id=? (repeated during serialization)
        """
        url = reverse("school_menu:get_schools_json_list")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url)

        assert response.status_code == 200

        # Analyze for duplicates
        analysis = analyze_duplicate_queries(context.captured_queries)
        print_duplicate_analysis("api_schools", analysis)

        # Report findings
        if analysis["duplicate_count"] > 0:
            print(
                f"WARNING: Found {analysis['duplicate_count']} duplicate query patterns"
            )
            print("This suggests N+1 query problems that should be optimized")

    def test_search_duplicate_queries(self, client, large_dataset):
        """
        Detect duplicate queries in search functionality

        N+1 pattern example:
        - Query 1: SELECT * FROM school WHERE is_published=True AND (name LIKE ? OR city LIKE ?)
        - Query 2-N: SELECT * FROM user WHERE id=? (if accessing school.user in template)
        """
        url = reverse("school_menu:search_schools")

        with CaptureQueriesContext(connection) as context:
            response = client.get(url, {"q": "school"})

        assert response.status_code == 200

        # Analyze for duplicates
        analysis = analyze_duplicate_queries(context.captured_queries)
        print_duplicate_analysis("search", analysis)

        # Report findings
        if analysis["duplicate_count"] > 0:
            print(
                f"WARNING: Found {analysis['duplicate_count']} duplicate query patterns"
            )
            print("This suggests N+1 query problems that should be optimized")

    def test_multiple_schools_detail_duplicate_queries(self, client, large_dataset):
        """
        Detect duplicate queries when accessing multiple school detail pages

        This test simulates real-world usage where users browse multiple schools.
        Helps identify if individual page queries are optimized.
        """
        # Test first 5 schools
        schools_to_test = large_dataset["schools"][:5]

        with CaptureQueriesContext(connection) as context:
            for school in schools_to_test:
                url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})
                response = client.get(url)
                assert response.status_code == 200

        # Analyze for duplicates
        analysis = analyze_duplicate_queries(context.captured_queries)
        print_duplicate_analysis("multiple_schools_detail", analysis)

        # Report findings
        if analysis["duplicate_count"] > 0:
            print(
                f"WARNING: Found {analysis['duplicate_count']} duplicate query patterns"
            )
            print("This suggests N+1 query problems that should be optimized")
