"""
Response time performance tests for monitoring and benchmarking

This module measures response times for critical views and endpoints to ensure
acceptable user experience. Tests use pytest-benchmark for accurate measurements
and calculate percentiles to understand worst-case scenarios.

Expected results:
- BEFORE optimization: 200-500ms with N+1 queries
- AFTER optimization: 50-100ms with optimizations + caching
- p99 (99th percentile) shows worst-case user experience
"""

import statistics
from pathlib import Path
from time import perf_counter

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_benchmark_results(test_name, stats):
    """
    Log benchmark results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        stats: Dictionary containing benchmark statistics
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Response Time Benchmark: {test_name}\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"Mean: {stats['mean']:.2f}ms\n")
        f.write(f"Min: {stats['min']:.2f}ms\n")
        f.write(f"Max: {stats['max']:.2f}ms\n")
        f.write(f"Stddev: {stats['stddev']:.2f}ms\n")
        if "p50" in stats:
            f.write(f"p50 (median): {stats['p50']:.2f}ms\n")
            f.write(f"p95: {stats['p95']:.2f}ms\n")
            f.write(f"p99: {stats['p99']:.2f}ms\n")
        f.write(f"{'=' * 80}\n\n")


def print_benchmark_results(test_name, stats):
    """
    Print benchmark results to console

    Args:
        test_name: Name of the test
        stats: Dictionary containing benchmark statistics
    """
    print(f"\n{'=' * 80}")
    print(f"Response Time Benchmark: {test_name}")
    print(f"{'=' * 80}")
    print(f"Mean: {stats['mean']:.2f}ms")
    print(f"Min: {stats['min']:.2f}ms")
    print(f"Max: {stats['max']:.2f}ms")
    print(f"Stddev: {stats['stddev']:.2f}ms")
    if "p50" in stats:
        print(f"p50 (median): {stats['p50']:.2f}ms")
        print(f"p95: {stats['p95']:.2f}ms")
        print(f"p99: {stats['p99']:.2f}ms")
    print(f"{'=' * 80}\n")


class TestSchoolListResponseTime:
    """Test response times for school list page"""

    def test_school_list_response_time(self, benchmark, client, large_dataset):
        """
        Benchmark response time for school list page

        Uses pytest-benchmark to measure accurate response times over multiple runs.
        pytest-benchmark automatically displays statistics after the test completes.
        """
        url = reverse("school_menu:school_list")

        def execute_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Run benchmark - pytest-benchmark will display results automatically
        benchmark(execute_request)


class TestSchoolDetailResponseTime:
    """Test response times for school detail page"""

    def test_school_detail_response_time(self, benchmark, client, large_dataset):
        """
        Benchmark response time for school detail page

        Uses pytest-benchmark to measure accurate response times over multiple runs.
        pytest-benchmark automatically displays statistics after the test completes.
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})

        def execute_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Run benchmark - pytest-benchmark will display results automatically
        benchmark(execute_request)


class TestAPIResponseTime:
    """Test response times for API endpoints"""

    def test_api_schools_list_response_time(self, benchmark, client, large_dataset):
        """
        Benchmark response time for API schools list endpoint

        Uses pytest-benchmark to measure accurate response times over multiple runs.
        pytest-benchmark automatically displays statistics after the test completes.
        """
        url = reverse("school_menu:get_schools_json_list")

        def execute_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Run benchmark - pytest-benchmark will display results automatically
        benchmark(execute_request)


class TestSearchResponseTime:
    """Test response times for search functionality"""

    def test_search_response_time(self, benchmark, client, large_dataset):
        """
        Benchmark response time for search functionality

        Uses pytest-benchmark to measure accurate response times over multiple runs.
        pytest-benchmark automatically displays statistics after the test completes.
        """
        url = reverse("school_menu:search_schools")

        def execute_request():
            response = client.get(url, {"q": "school"})
            assert response.status_code == 200
            return response

        # Run benchmark - pytest-benchmark will display results automatically
        benchmark(execute_request)


class TestResponseTimePercentiles:
    """Test response time percentiles to understand worst-case scenarios"""

    def test_school_list_percentiles(self, client, large_dataset):
        """
        Calculate p50, p95, p99 percentiles for school list page

        Percentiles help understand worst-case user experience:
        - p50 (median): typical user experience
        - p95: 95% of users experience this or better
        - p99: worst-case for 99% of users
        """
        url = reverse("school_menu:school_list")
        response_times = []

        # Make 100 requests to gather data
        for _ in range(100):
            start = perf_counter()
            response = client.get(url)
            end = perf_counter()

            assert response.status_code == 200
            response_times.append((end - start) * 1000)  # Convert to ms

        # Calculate statistics
        stats = {
            "mean": statistics.mean(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "stddev": statistics.stdev(response_times),
            "p50": statistics.quantiles(response_times, n=100)[49],  # 50th percentile
            "p95": statistics.quantiles(response_times, n=100)[94],  # 95th percentile
            "p99": statistics.quantiles(response_times, n=100)[98],  # 99th percentile
        }

        # Log and print results
        log_benchmark_results("school_list_percentiles", stats)
        print_benchmark_results("school_list_percentiles", stats)

        # Assert p99 is acceptable even before optimization
        assert stats["p99"] < 1000, (
            f"p99 response time {stats['p99']:.2f}ms exceeds 1000ms threshold"
        )

    def test_school_detail_percentiles(self, client, large_dataset):
        """
        Calculate p50, p95, p99 percentiles for school detail page

        Percentiles help understand worst-case user experience.
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})
        response_times = []

        # Make 100 requests to gather data
        for _ in range(100):
            start = perf_counter()
            response = client.get(url)
            end = perf_counter()

            assert response.status_code == 200
            response_times.append((end - start) * 1000)  # Convert to ms

        # Calculate statistics
        stats = {
            "mean": statistics.mean(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "stddev": statistics.stdev(response_times),
            "p50": statistics.quantiles(response_times, n=100)[49],  # 50th percentile
            "p95": statistics.quantiles(response_times, n=100)[94],  # 95th percentile
            "p99": statistics.quantiles(response_times, n=100)[98],  # 99th percentile
        }

        # Log and print results
        log_benchmark_results("school_detail_percentiles", stats)
        print_benchmark_results("school_detail_percentiles", stats)

        # Assert p99 is acceptable even before optimization
        assert stats["p99"] < 1000, (
            f"p99 response time {stats['p99']:.2f}ms exceeds 1000ms threshold"
        )

    def test_api_schools_percentiles(self, client, large_dataset):
        """
        Calculate p50, p95, p99 percentiles for API schools list

        Percentiles help understand worst-case user experience.
        """
        url = reverse("school_menu:get_schools_json_list")
        response_times = []

        # Make 100 requests to gather data
        for _ in range(100):
            start = perf_counter()
            response = client.get(url)
            end = perf_counter()

            assert response.status_code == 200
            response_times.append((end - start) * 1000)  # Convert to ms

        # Calculate statistics
        stats = {
            "mean": statistics.mean(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "stddev": statistics.stdev(response_times),
            "p50": statistics.quantiles(response_times, n=100)[49],  # 50th percentile
            "p95": statistics.quantiles(response_times, n=100)[94],  # 95th percentile
            "p99": statistics.quantiles(response_times, n=100)[98],  # 99th percentile
        }

        # Log and print results
        log_benchmark_results("api_schools_percentiles", stats)
        print_benchmark_results("api_schools_percentiles", stats)

        # Assert p99 is acceptable even before optimization
        assert stats["p99"] < 1000, (
            f"p99 response time {stats['p99']:.2f}ms exceeds 1000ms threshold"
        )

    def test_search_percentiles(self, client, large_dataset):
        """
        Calculate p50, p95, p99 percentiles for search functionality

        Percentiles help understand worst-case user experience.
        """
        url = reverse("school_menu:search_schools")
        response_times = []

        # Make 100 requests to gather data
        for _ in range(100):
            start = perf_counter()
            response = client.get(url, {"q": "school"})
            end = perf_counter()

            assert response.status_code == 200
            response_times.append((end - start) * 1000)  # Convert to ms

        # Calculate statistics
        stats = {
            "mean": statistics.mean(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "stddev": statistics.stdev(response_times),
            "p50": statistics.quantiles(response_times, n=100)[49],  # 50th percentile
            "p95": statistics.quantiles(response_times, n=100)[94],  # 95th percentile
            "p99": statistics.quantiles(response_times, n=100)[98],  # 99th percentile
        }

        # Log and print results
        log_benchmark_results("search_percentiles", stats)
        print_benchmark_results("search_percentiles", stats)

        # Assert p99 is acceptable even before optimization
        assert stats["p99"] < 1000, (
            f"p99 response time {stats['p99']:.2f}ms exceeds 1000ms threshold"
        )
