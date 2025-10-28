"""
Memory profiling tests for monitoring resource usage

This module profiles memory usage during request processing to identify
potential memory leaks or excessive consumption. Memory profiling helps
ensure the application scales efficiently and doesn't exhaust server resources.

Expected results:
- Max memory usage < 500MB during request processing
- No memory leaks (stable memory usage across repeated requests)
- Reasonable memory consumption for typical operations
"""

from pathlib import Path

import pytest
from django.urls import reverse
from memory_profiler import memory_usage

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_memory_results(test_name, stats):
    """
    Log memory results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        stats: Dictionary containing memory statistics
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Memory Usage Test: {test_name}\n")
        f.write(f"{'=' * 80}\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
        f.write(f"{'=' * 80}\n\n")


def print_memory_results(test_name, stats):
    """
    Print memory results to console

    Args:
        test_name: Name of the test
        stats: Dictionary containing memory statistics
    """
    print(f"\n{'=' * 80}")
    print(f"Memory Usage Test: {test_name}")
    print(f"{'=' * 80}")
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(f"{'=' * 80}\n")


class TestMemoryUsage:
    """Test memory usage during request processing"""

    def test_school_list_memory_usage(self, client, large_dataset):
        """
        Profile memory usage when rendering school list page

        This test uses memory-profiler to track memory consumption during
        request processing. It samples memory usage at 0.1 second intervals
        to capture peak memory usage.

        Process:
        1. Define a function that makes the request
        2. Use memory_usage() to profile the function execution
        3. Calculate max and average memory from samples
        4. Assert max memory < 500MB

        Expected: Reasonable memory usage without leaks
        """
        url = reverse("school_menu:school_list")

        # Define function to profile
        def make_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Profile memory usage
        # interval=0.1 means sample every 0.1 seconds
        # max_usage=True returns maximum memory used
        mem_usage = memory_usage(
            make_request,
            interval=0.1,
            max_usage=False,  # Return list of measurements
        )

        # Calculate statistics
        max_memory = max(mem_usage)
        avg_memory = sum(mem_usage) / len(mem_usage)
        min_memory = min(mem_usage)
        memory_range = max_memory - min_memory
        num_samples = len(mem_usage)

        stats = {
            "Number of samples": num_samples,
            "Max memory usage": f"{max_memory:.2f} MB",
            "Average memory usage": f"{avg_memory:.2f} MB",
            "Min memory usage": f"{min_memory:.2f} MB",
            "Memory range": f"{memory_range:.2f} MB",
            "Max memory threshold": "500 MB",
            "Memory check": "PASS" if max_memory < 500 else "WARNING",
        }

        # Log and print results
        log_memory_results("school_list_memory_usage", stats)
        print_memory_results("school_list_memory_usage", stats)

        # Assert max memory is reasonable
        assert max_memory < 500, (
            f"Max memory usage {max_memory:.2f}MB exceeds 500MB threshold"
        )

    def test_school_detail_memory_usage(self, client, large_dataset):
        """
        Profile memory usage when rendering school detail page

        Similar to school list test, but profiles the detail page which
        includes menu data rendering.
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})

        def make_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Profile memory usage
        mem_usage = memory_usage(make_request, interval=0.1, max_usage=False)

        # Calculate statistics
        max_memory = max(mem_usage)
        avg_memory = sum(mem_usage) / len(mem_usage)
        min_memory = min(mem_usage)
        memory_range = max_memory - min_memory
        num_samples = len(mem_usage)

        stats = {
            "Number of samples": num_samples,
            "Max memory usage": f"{max_memory:.2f} MB",
            "Average memory usage": f"{avg_memory:.2f} MB",
            "Min memory usage": f"{min_memory:.2f} MB",
            "Memory range": f"{memory_range:.2f} MB",
            "Max memory threshold": "500 MB",
            "Memory check": "PASS" if max_memory < 500 else "WARNING",
        }

        # Log and print results
        log_memory_results("school_detail_memory_usage", stats)
        print_memory_results("school_detail_memory_usage", stats)

        # Assert max memory is reasonable
        assert max_memory < 500, (
            f"Max memory usage {max_memory:.2f}MB exceeds 500MB threshold"
        )

    def test_api_memory_usage(self, client, large_dataset):
        """
        Profile memory usage for API endpoint

        Tests memory usage when serializing and returning JSON data
        for all schools.
        """
        url = reverse("school_menu:get_schools_json_list")

        def make_request():
            response = client.get(url)
            assert response.status_code == 200
            return response

        # Profile memory usage
        mem_usage = memory_usage(make_request, interval=0.1, max_usage=False)

        # Calculate statistics
        max_memory = max(mem_usage)
        avg_memory = sum(mem_usage) / len(mem_usage)
        min_memory = min(mem_usage)
        memory_range = max_memory - min_memory
        num_samples = len(mem_usage)

        stats = {
            "Number of samples": num_samples,
            "Max memory usage": f"{max_memory:.2f} MB",
            "Average memory usage": f"{avg_memory:.2f} MB",
            "Min memory usage": f"{min_memory:.2f} MB",
            "Memory range": f"{memory_range:.2f} MB",
            "Max memory threshold": "500 MB",
            "Memory check": "PASS" if max_memory < 500 else "WARNING",
        }

        # Log and print results
        log_memory_results("api_schools_list_memory_usage", stats)
        print_memory_results("api_schools_list_memory_usage", stats)

        # Assert max memory is reasonable
        assert max_memory < 500, (
            f"Max memory usage {max_memory:.2f}MB exceeds 500MB threshold"
        )

    def test_memory_leak_detection(self, client, large_dataset):
        """
        Test for memory leaks by making repeated requests

        This test makes multiple requests to the same endpoint and monitors
        memory usage. If there's a memory leak, memory usage will grow with
        each request. Stable memory indicates no leaks.
        """
        url = reverse("school_menu:school_list")

        def make_multiple_requests():
            # Make 10 requests and track memory after each
            for _ in range(10):
                response = client.get(url)
                assert response.status_code == 200

        # Profile memory usage over multiple requests
        mem_usage = memory_usage(make_multiple_requests, interval=0.1, max_usage=False)

        # Analyze memory trend
        max_memory = max(mem_usage)
        avg_memory = sum(mem_usage) / len(mem_usage)
        min_memory = min(mem_usage)
        memory_growth = max_memory - min_memory
        num_samples = len(mem_usage)

        # Check if memory grows significantly (potential leak indicator)
        # Growth > 100MB over 10 requests could indicate a leak
        potential_leak = memory_growth > 100

        stats = {
            "Number of requests": 10,
            "Number of samples": num_samples,
            "Max memory usage": f"{max_memory:.2f} MB",
            "Average memory usage": f"{avg_memory:.2f} MB",
            "Min memory usage": f"{min_memory:.2f} MB",
            "Memory growth": f"{memory_growth:.2f} MB",
            "Leak detection threshold": "100 MB growth",
            "Potential leak detected": "YES" if potential_leak else "NO",
        }

        # Log and print results
        log_memory_results("memory_leak_detection", stats)
        print_memory_results("memory_leak_detection", stats)

        # Warn if potential leak detected
        if potential_leak:
            print(
                f"WARNING: Memory grew by {memory_growth:.2f}MB over 10 requests. "
                "This could indicate a memory leak."
            )

        # Assert no significant memory leak
        assert not potential_leak, (
            f"Potential memory leak detected: {memory_growth:.2f}MB growth"
        )
