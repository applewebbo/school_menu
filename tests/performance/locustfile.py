"""
Locust load testing suite for school menu application

This module simulates realistic user behavior patterns to identify performance
bottlenecks under concurrent user load. It includes two user types:
- SchoolMenuUser: Simulates typical browsing behavior with weighted tasks
- StressTestUser: Simulates rapid requests for stress testing

Run with:
    locust -f tests/performance/locustfile.py --host=http://localhost:8000

Web UI available at: http://localhost:8089 (when not headless)
"""

from datetime import datetime
from pathlib import Path

from locust import HttpUser, between, events, task

# Path for load test results logging
LOAD_TEST_RESULTS_FILE = Path(__file__).parent / "load_test_results.txt"

# Store request statistics globally
request_stats = {
    "total_requests": 0,
    "failed_requests": 0,
    "response_times": [],
}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Event listener called when load test starts
    Initializes metrics tracking
    """
    print("=" * 80)
    print(f"Load test started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Reset stats
    request_stats["total_requests"] = 0
    request_stats["failed_requests"] = 0
    request_stats["response_times"] = []


@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, exception, context, **kwargs
):
    """
    Event listener called for each request
    Tracks request metrics
    """
    request_stats["total_requests"] += 1
    request_stats["response_times"].append(response_time)

    if exception:
        request_stats["failed_requests"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Event listener called when load test stops
    Calculates and saves summary statistics
    """
    print("\n" + "=" * 80)
    print("Load test completed - Calculating statistics...")
    print("=" * 80)

    # Calculate statistics
    total_requests = request_stats["total_requests"]
    failed_requests = request_stats["failed_requests"]
    success_rate = (
        ((total_requests - failed_requests) / total_requests * 100)
        if total_requests > 0
        else 0
    )

    response_times = sorted(request_stats["response_times"])
    if response_times:
        median_time = response_times[len(response_times) // 2]
        p95_time = response_times[int(len(response_times) * 0.95)]
        p99_time = response_times[int(len(response_times) * 0.99)]
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
    else:
        median_time = p95_time = p99_time = avg_time = min_time = max_time = 0

    # Get RPS from Locust stats
    stats = environment.stats
    total_rps = stats.total.total_rps if hasattr(stats.total, "total_rps") else 0

    # Prepare summary
    summary = f"""
{"=" * 80}
Load Test Summary
{"=" * 80}
Test completed at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Request Statistics:
  Total requests: {total_requests}
  Failed requests: {failed_requests}
  Success rate: {success_rate:.1f}%
  Requests per second (RPS): {total_rps:.2f}

Response Times (ms):
  Average: {avg_time:.2f}
  Median (p50): {median_time:.2f}
  95th percentile (p95): {p95_time:.2f}
  99th percentile (p99): {p99_time:.2f}
  Min: {min_time:.2f}
  Max: {max_time:.2f}
{"=" * 80}
"""

    # Print to console
    print(summary)

    # Save to file
    with open(LOAD_TEST_RESULTS_FILE, "a") as f:
        f.write(summary)
        f.write("\n")


class SchoolMenuUser(HttpUser):
    """
    Simulates typical user browsing behavior with weighted tasks

    This user class represents normal application usage with realistic
    wait times between actions. Tasks are weighted based on typical usage:
    - School list browsing: most common (weight=5)
    - School detail viewing: common (weight=3)
    - Search functionality: occasional (weight=2)
    - API access: rare (weight=1)
    """

    # Wait between 1 and 5 seconds between tasks (realistic user behavior)
    wait_time = between(1, 5)

    def on_start(self):
        """Called when a user starts - fetch school list to get slugs"""
        response = self.client.get("/json/schools/")
        if response.status_code == 200:
            schools = response.json()
            # Store a few school slugs for later use
            self.school_slugs = [
                school["url"].split("/")[-2] for school in schools[:10]
            ]
        else:
            self.school_slugs = ["test-school"]

    @task(5)
    def view_school_list(self):
        """View the school list page - most common action (weight=5)"""
        self.client.get("/school_list", name="School List")

    @task(3)
    def view_school_detail(self):
        """View a school detail page - common action (weight=3)"""
        if hasattr(self, "school_slugs") and self.school_slugs:
            slug = self.school_slugs[0]
            self.client.get(f"/menu/{slug}/", name="School Detail")

    @task(2)
    def search_schools(self):
        """Search for schools - occasional action (weight=2)"""
        self.client.get("/search-schools/?q=school", name="Search Schools")

    @task(1)
    def api_schools_list(self):
        """Access API schools list - rare action (weight=1)"""
        self.client.get("/json/schools/", name="API Schools List")

    @task(1)
    def api_school_menu(self):
        """Access API school menu - rare action (weight=1)"""
        if hasattr(self, "school_slugs") and self.school_slugs:
            slug = self.school_slugs[0]
            self.client.get(f"/json/menu/{slug}/", name="API School Menu")


class StressTestUser(HttpUser):
    """
    Simulates rapid requests for stress testing

    This user class represents aggressive usage patterns with minimal
    wait times between requests. Useful for identifying breaking points
    and performance degradation under heavy load.
    """

    # Very short wait time (0.1 to 0.5 seconds) for stress testing
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Called when a user starts - fetch school list to get slugs"""
        response = self.client.get("/json/schools/")
        if response.status_code == 200:
            schools = response.json()
            self.school_slugs = [
                school["url"].split("/")[-2] for school in schools[:10]
            ]
        else:
            self.school_slugs = ["test-school"]

    @task(1)
    def rapid_school_list(self):
        """Rapid requests to school list"""
        self.client.get("/school_list", name="Stress: School List")

    @task(1)
    def rapid_api_access(self):
        """Rapid API requests"""
        self.client.get("/json/schools/", name="Stress: API Schools")

    @task(1)
    def rapid_search(self):
        """Rapid search requests"""
        self.client.get("/search-schools/?q=test", name="Stress: Search")
