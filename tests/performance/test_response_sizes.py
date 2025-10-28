"""
Response size and bandwidth tests for monitoring transfer sizes

This module measures response sizes (uncompressed and compressed) to validate
compression effectiveness and monitor bandwidth usage. This is important for
mobile users who may have limited data plans.

Expected results:
- BEFORE compression: 100-200KB for large pages
- AFTER compression: 30-60KB (70% reduction with gzip)
- Static files should have .gz and .br pre-compressed versions
"""

import gzip
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.performance]

# Path for baseline metrics logging
BASELINE_METRICS_FILE = Path(__file__).parent / "baseline_metrics.txt"


def log_size_results(test_name, stats):
    """
    Log size results to baseline_metrics.txt for tracking over time

    Args:
        test_name: Name of the test
        stats: Dictionary containing size statistics
    """
    with open(BASELINE_METRICS_FILE, "a") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"Response Size Test: {test_name}\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"Uncompressed: {stats['uncompressed_bytes']} bytes ")
        f.write(f"({stats['uncompressed_kb']:.2f} KB)\n")
        if "compressed_bytes" in stats:
            f.write(f"Compressed (gzip): {stats['compressed_bytes']} bytes ")
            f.write(f"({stats['compressed_kb']:.2f} KB)\n")
            f.write(f"Compression ratio: {stats['compression_ratio']:.1f}%\n")
            f.write(
                f"Size reduction: {stats['size_reduction']:.1f}% "
                f"({stats['bytes_saved']} bytes saved)\n"
            )
        f.write(f"{'=' * 80}\n\n")


def print_size_results(test_name, stats):
    """
    Print size results to console

    Args:
        test_name: Name of the test
        stats: Dictionary containing size statistics
    """
    print(f"\n{'=' * 80}")
    print(f"Response Size Test: {test_name}")
    print(f"{'=' * 80}")
    print(
        f"Uncompressed: {stats['uncompressed_bytes']} bytes "
        f"({stats['uncompressed_kb']:.2f} KB)"
    )
    if "compressed_bytes" in stats:
        print(
            f"Compressed (gzip): {stats['compressed_bytes']} bytes "
            f"({stats['compressed_kb']:.2f} KB)"
        )
        print(f"Compression ratio: {stats['compression_ratio']:.1f}%")
        print(
            f"Size reduction: {stats['size_reduction']:.1f}% "
            f"({stats['bytes_saved']} bytes saved)"
        )
    print(f"{'=' * 80}\n")


def calculate_compression_stats(uncompressed_content):
    """
    Calculate compression statistics for content

    Args:
        uncompressed_content: Content as bytes

    Returns:
        dict: Statistics including sizes and ratios
    """
    uncompressed_bytes = len(uncompressed_content)
    compressed_content = gzip.compress(uncompressed_content)
    compressed_bytes = len(compressed_content)

    return {
        "uncompressed_bytes": uncompressed_bytes,
        "uncompressed_kb": uncompressed_bytes / 1024,
        "compressed_bytes": compressed_bytes,
        "compressed_kb": compressed_bytes / 1024,
        "compression_ratio": (compressed_bytes / uncompressed_bytes) * 100,
        "size_reduction": ((uncompressed_bytes - compressed_bytes) / uncompressed_bytes)
        * 100,
        "bytes_saved": uncompressed_bytes - compressed_bytes,
    }


class TestHTMLResponseSizes:
    """Test response sizes for HTML pages"""

    def test_school_list_size(self, client, large_dataset):
        """
        Measure school list page size (uncompressed and gzip compressed)

        This page lists all schools, so with a large dataset it could be significant.
        """
        url = reverse("school_menu:school_list")
        response = client.get(url)

        assert response.status_code == 200

        # Get uncompressed content
        content = response.content

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Log and print results
        log_size_results("school_list_html", stats)
        print_size_results("school_list_html", stats)

    def test_school_detail_size(self, client, large_dataset):
        """
        Measure school detail page size (uncompressed and gzip compressed)

        Detail pages include menu data which can add to the size.
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:school_menu", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200

        # Get uncompressed content
        content = response.content

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Log and print results
        log_size_results("school_detail_html", stats)
        print_size_results("school_detail_html", stats)


class TestAPIResponseSizes:
    """Test response sizes for API endpoints"""

    def test_api_schools_list_size(self, client, large_dataset):
        """
        Measure API schools list size with compression

        JSON APIs should use compression to reduce bandwidth usage.
        With 100 schools, this tests a realistic dataset.
        """
        url = reverse("school_menu:get_schools_json_list")
        response = client.get(url)

        assert response.status_code == 200

        # Get uncompressed content
        content = response.content

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Log and print results
        log_size_results("api_schools_list_json", stats)
        print_size_results("api_schools_list_json", stats)

    def test_api_school_menu_size(self, client, large_dataset):
        """
        Measure API school menu size with compression

        Menu data APIs return meal information which can be substantial.
        """
        school = large_dataset["schools"][0]
        url = reverse("school_menu:get_school_json_menu", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200

        # Get uncompressed content
        content = response.content

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Log and print results
        log_size_results("api_school_menu_json", stats)
        print_size_results("api_school_menu_json", stats)


class TestStaticFileSizes:
    """Test static file sizes and pre-compressed versions"""

    def test_tailwind_css_size(self):
        """
        Measure tailwind.css size and check for pre-compressed versions

        Tailwind CSS can be large - compression is essential.
        Checks for .gz and .br (brotli) pre-compressed versions.
        """
        static_dir = Path(settings.BASE_DIR) / "static"
        css_file = static_dir / "css" / "tailwind.css"

        assert css_file.exists(), f"tailwind.css not found at {css_file}"

        # Read file content
        content = css_file.read_bytes()

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Check for pre-compressed versions
        gz_file = css_file.with_suffix(".css.gz")
        br_file = css_file.with_suffix(".css.br")

        stats["has_gz_version"] = gz_file.exists()
        stats["has_br_version"] = br_file.exists()

        # Log and print results
        log_size_results("tailwind_css", stats)
        print_size_results("tailwind_css", stats)

        # Print warnings if pre-compressed versions don't exist
        if not stats["has_gz_version"]:
            print("WARNING: No .gz pre-compressed version found for tailwind.css")
        if not stats["has_br_version"]:
            print("WARNING: No .br pre-compressed version found for tailwind.css")

    def test_htmx_js_size(self):
        """
        Measure htmx.min.js size and check for pre-compressed versions

        HTMX is already minified, but compression can still help.
        """
        static_dir = Path(settings.BASE_DIR) / "static"
        js_file = static_dir / "js" / "htmx.min.js"

        assert js_file.exists(), f"htmx.min.js not found at {js_file}"

        # Read file content
        content = js_file.read_bytes()

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Check for pre-compressed versions
        gz_file = Path(str(js_file) + ".gz")
        br_file = Path(str(js_file) + ".br")

        stats["has_gz_version"] = gz_file.exists()
        stats["has_br_version"] = br_file.exists()

        # Log and print results
        log_size_results("htmx_min_js", stats)
        print_size_results("htmx_min_js", stats)

        # Print warnings if pre-compressed versions don't exist
        if not stats["has_gz_version"]:
            print("WARNING: No .gz pre-compressed version found for htmx.min.js")
        if not stats["has_br_version"]:
            print("WARNING: No .br pre-compressed version found for htmx.min.js")

    def test_alpine_js_size(self):
        """
        Measure alpine.min.js size and check for pre-compressed versions

        Alpine is already minified, but compression can still help.
        """
        static_dir = Path(settings.BASE_DIR) / "static"
        js_file = static_dir / "js" / "alpine.min.js"

        assert js_file.exists(), f"alpine.min.js not found at {js_file}"

        # Read file content
        content = js_file.read_bytes()

        # Calculate compression stats
        stats = calculate_compression_stats(content)

        # Check for pre-compressed versions
        gz_file = Path(str(js_file) + ".gz")
        br_file = Path(str(js_file) + ".br")

        stats["has_gz_version"] = gz_file.exists()
        stats["has_br_version"] = br_file.exists()

        # Log and print results
        log_size_results("alpine_min_js", stats)
        print_size_results("alpine_min_js", stats)

        # Print warnings if pre-compressed versions don't exist
        if not stats["has_gz_version"]:
            print("WARNING: No .gz pre-compressed version found for alpine.min.js")
        if not stats["has_br_version"]:
            print("WARNING: No .br pre-compressed version found for alpine.min.js")
