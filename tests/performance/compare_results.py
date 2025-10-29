#!/usr/bin/env python
"""
Compare baseline vs optimized performance metrics.

This script loads both baseline_metrics.txt and optimized_metrics.txt,
calculates percentage improvements, and displays a formatted comparison table.
"""

import re
from pathlib import Path


def parse_metrics_simple(file_path: Path) -> dict:
    """Parse metrics file and extract key performance indicators."""
    metrics = {}

    with open(file_path) as f:
        content = f.read()

    # Parse query counts
    query_pattern = r"Test: (\w+)\nTotal Queries: (\d+)"
    for match in re.finditer(query_pattern, content):
        test_name, query_count = match.groups()
        metrics[f"{test_name}_queries"] = int(query_count)

    # Parse response times (p95 is most important metric)
    time_pattern = (
        r"Response Time Benchmark: (\w+)\n={80}\n"
        r"Mean: ([\d.]+)ms\n"
        r"Min: ([\d.]+)ms\n"
        r"Max: ([\d.]+)ms\n"
        r"Stddev: ([\d.]+)ms\n"
        r"p50 \(median\): ([\d.]+)ms\n"
        r"p95: ([\d.]+)ms\n"
        r"p99: ([\d.]+)ms"
    )
    for match in re.finditer(time_pattern, content):
        test_name, mean, _, _, _, _, p95, _ = match.groups()
        metrics[f"{test_name}_mean_ms"] = float(mean)
        metrics[f"{test_name}_p95_ms"] = float(p95)

    # Parse response sizes
    size_pattern = (
        r"Response Size Test: (\w+)\n={80}\n"
        r"Uncompressed: (\d+) bytes \(([\d.]+) KB\)\n"
        r"Compressed \(gzip\): (\d+) bytes"
    )
    for match in re.finditer(size_pattern, content):
        test_name, _, uncomp_kb, comp_bytes = match.groups()
        metrics[f"{test_name}_uncompressed_kb"] = float(uncomp_kb)
        metrics[f"{test_name}_compressed_bytes"] = int(comp_bytes)

    # Parse cache hit rate
    cache_hit_pattern = r"Estimated cache hit rate: ([\d.]+)%"
    cache_hits = list(re.finditer(cache_hit_pattern, content))
    if cache_hits:
        metrics["cache_hit_rate_pct"] = float(cache_hits[0].group(1))

    # Parse memory usage
    memory_pattern = (
        r"Memory Usage Test: school_list_memory_usage\n={80}\n"
        r"Number of samples: (\d+)\n"
        r"Max memory usage: ([\d.]+) MB"
    )
    memory_matches = list(re.finditer(memory_pattern, content))
    if memory_matches:
        # Get the first occurrence
        metrics["memory_max_mb"] = float(memory_matches[0].group(2))

    # Parse task performance
    task_queries_pattern = (
        r"Task Performance Test: notification_task_baseline\n={80}\n"
        r"Total subscribers: (\d+)\n"
        r"Number of schools: (\d+)\n"
        r"Subscribers per school: (\d+)\n"
        r"Total database queries: (\d+)\n"
        r"Total duration: ([\d.]+)ms"
    )
    task_matches = list(re.finditer(task_queries_pattern, content))
    if task_matches:
        # Get the first occurrence
        match = task_matches[0]
        metrics["task_queries"] = int(match.group(4))
        metrics["task_duration_ms"] = float(match.group(5))

    return metrics


def calculate_change(
    baseline: float, optimized: float, lower_is_better: bool = True
) -> tuple[float, str]:
    """
    Calculate percentage change and determine if it's an improvement.

    Args:
        baseline: Baseline metric value
        optimized: Optimized metric value
        lower_is_better: True if lower values are better (queries, time, size)

    Returns:
        Tuple of (percentage_change, arrow_symbol)
    """
    if baseline == 0:
        return 0.0, "-"

    change = ((optimized - baseline) / baseline) * 100

    # Handle no change
    if change == 0:
        return 0.0, "-"

    if lower_is_better:
        # For metrics where lower is better (queries, response time, size)
        arrow = "↓" if change < 0 else "↑"
    else:
        # For metrics where higher is better (cache hit rate)
        arrow = "↑" if change > 0 else "↓"

    return change, arrow


def format_comparison_table(baseline_metrics: dict, optimized_metrics: dict) -> str:
    """Generate formatted comparison table."""
    output = []
    output.append("=" * 100)
    output.append("PERFORMANCE COMPARISON: BASELINE vs OPTIMIZED")
    output.append("=" * 100)
    output.append("")

    # Database Query Comparisons
    output.append("📊 DATABASE QUERIES")
    output.append("-" * 100)
    output.append(
        f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
    )
    output.append("-" * 100)

    query_metrics = [
        ("school_list_baseline_queries", "School List Queries"),
        ("school_detail_baseline_queries", "School Detail Queries"),
        ("api_schools_baseline_queries", "API Schools Queries"),
        ("search_baseline_queries", "Search Queries"),
    ]

    for metric_key, label in query_metrics:
        if metric_key in baseline_metrics and metric_key in optimized_metrics:
            baseline = baseline_metrics[metric_key]
            optimized = optimized_metrics[metric_key]
            change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
            status = (
                "✅ Better"
                if arrow == "↓"
                else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
            )
            output.append(
                f"{label:<40} {baseline:>15.0f} {optimized:>15.0f} "
                f"{change:>13.1f}% {arrow} {status:>10}"
            )

    output.append("")

    # Response Time Comparisons
    output.append("⏱️  RESPONSE TIMES (p95)")
    output.append("-" * 100)
    output.append(
        f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
    )
    output.append("-" * 100)

    time_metrics = [
        ("school_list_percentiles_p95_ms", "School List p95"),
        ("school_detail_percentiles_p95_ms", "School Detail p95"),
        ("api_schools_percentiles_p95_ms", "API Schools p95"),
        ("search_percentiles_p95_ms", "Search p95"),
    ]

    for metric_key, label in time_metrics:
        if metric_key in baseline_metrics and metric_key in optimized_metrics:
            baseline = baseline_metrics[metric_key]
            optimized = optimized_metrics[metric_key]
            change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
            status = (
                "✅ Better"
                if arrow == "↓"
                else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
            )
            output.append(
                f"{label:<40} {baseline:>13.2f} ms {optimized:>13.2f} ms "
                f"{change:>13.1f}% {arrow} {status:>10}"
            )

    output.append("")

    # Response Size Comparisons
    output.append("📦 RESPONSE SIZES (Compressed)")
    output.append("-" * 100)
    output.append(
        f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
    )
    output.append("-" * 100)

    size_metrics = [
        ("school_list_html_compressed_bytes", "School List HTML"),
        ("school_detail_html_compressed_bytes", "School Detail HTML"),
        ("tailwind_css_compressed_bytes", "Tailwind CSS"),
    ]

    for metric_key, label in size_metrics:
        if metric_key in baseline_metrics and metric_key in optimized_metrics:
            baseline = baseline_metrics[metric_key]
            optimized = optimized_metrics[metric_key]
            change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
            status = (
                "✅ Better"
                if arrow == "↓"
                else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
            )
            baseline_kb = baseline / 1024
            optimized_kb = optimized / 1024
            output.append(
                f"{label:<40} {baseline_kb:>12.2f} KB {optimized_kb:>12.2f} KB "
                f"{change:>13.1f}% {arrow} {status:>10}"
            )

    output.append("")

    # Cache Performance
    if (
        "cache_hit_rate_pct" in baseline_metrics
        and "cache_hit_rate_pct" in optimized_metrics
    ):
        output.append("💾 CACHE PERFORMANCE")
        output.append("-" * 100)
        output.append(
            f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
        )
        output.append("-" * 100)

        baseline = baseline_metrics["cache_hit_rate_pct"]
        optimized = optimized_metrics["cache_hit_rate_pct"]
        change, arrow = calculate_change(baseline, optimized, lower_is_better=False)
        status = (
            "✅ Better" if arrow == "↑" else ("⚠️ Worse" if arrow == "↓" else "➡️ Same")
        )
        output.append(
            f"{'Cache Hit Rate':<40} {baseline:>13.1f}% {optimized:>13.1f}% "
            f"{change:>13.1f}% {arrow} {status:>10}"
        )
        output.append("")

    # Memory Usage
    if "memory_max_mb" in baseline_metrics and "memory_max_mb" in optimized_metrics:
        output.append("🧠 MEMORY USAGE")
        output.append("-" * 100)
        output.append(
            f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
        )
        output.append("-" * 100)

        baseline = baseline_metrics["memory_max_mb"]
        optimized = optimized_metrics["memory_max_mb"]
        change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
        status = (
            "✅ Better" if arrow == "↓" else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
        )
        output.append(
            f"{'Max Memory Usage':<40} {baseline:>12.2f} MB {optimized:>12.2f} MB "
            f"{change:>13.1f}% {arrow} {status:>10}"
        )
        output.append("")

    # Task Performance
    if "task_queries" in baseline_metrics and "task_queries" in optimized_metrics:
        output.append("🔄 BACKGROUND TASK PERFORMANCE")
        output.append("-" * 100)
        output.append(
            f"{'Metric':<40} {'Baseline':>15} {'Optimized':>15} {'Change':>15} {'Status':>10}"
        )
        output.append("-" * 100)

        baseline = baseline_metrics["task_queries"]
        optimized = optimized_metrics["task_queries"]
        change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
        status = (
            "✅ Better" if arrow == "↓" else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
        )
        output.append(
            f"{'Notification Task Queries':<40} {baseline:>15.0f} {optimized:>15.0f} "
            f"{change:>13.1f}% {arrow} {status:>10}"
        )

        if (
            "task_duration_ms" in baseline_metrics
            and "task_duration_ms" in optimized_metrics
        ):
            baseline = baseline_metrics["task_duration_ms"]
            optimized = optimized_metrics["task_duration_ms"]
            change, arrow = calculate_change(baseline, optimized, lower_is_better=True)
            status = (
                "✅ Better"
                if arrow == "↓"
                else ("⚠️ Worse" if arrow == "↑" else "➡️ Same")
            )
            output.append(
                f"{'Task Duration':<40} {baseline:>12.2f} ms {optimized:>12.2f} ms "
                f"{change:>13.1f}% {arrow} {status:>10}"
            )
        output.append("")

    # Summary
    output.append("=" * 100)
    output.append("SUMMARY")
    output.append("=" * 100)
    output.append("")
    output.append("Legend:")
    output.append("  ↓ = Improvement (lower is better)")
    output.append("  ↑ = Improvement (higher is better) / Regression (lower is better)")
    output.append("  ✅ Better = Metric improved after optimization")
    output.append("  ⚠️ Worse = Metric regressed after optimization")
    output.append("  ➡️ Same = No change")
    output.append("")

    return "\n".join(output)


def main():
    """Main entry point for metrics comparison."""
    script_dir = Path(__file__).parent
    baseline_file = script_dir / "baseline_metrics.txt"
    optimized_file = script_dir / "optimized_metrics.txt"

    # Check if baseline file exists
    if not baseline_file.exists():
        print(f"❌ Error: Baseline metrics file not found: {baseline_file}")
        print("Run performance tests first to generate baseline metrics.")
        return 1

    # Check if optimized file exists
    if not optimized_file.exists():
        print("⚠️  Warning: Optimized metrics file not found.")
        print(f"Expected location: {optimized_file}")
        print("")
        print("To generate optimized metrics:")
        print("1. Apply performance optimizations to your code")
        print("2. Run performance tests again")
        print("3. Copy baseline_metrics.txt to optimized_metrics.txt")
        print("")
        print(
            "For now, creating a comparison with baseline vs baseline (no changes)..."
        )
        optimized_file = baseline_file

    print("📊 Loading baseline metrics...")
    baseline_metrics = parse_metrics_simple(baseline_file)

    print("📊 Loading optimized metrics...")
    optimized_metrics = parse_metrics_simple(optimized_file)

    print("\n" + "=" * 100)
    print("Metrics loaded successfully!")
    print(f"Baseline metrics: {len(baseline_metrics)} metrics")
    print(f"Optimized metrics: {len(optimized_metrics)} metrics")
    print("=" * 100 + "\n")

    # Generate and display comparison
    comparison = format_comparison_table(baseline_metrics, optimized_metrics)
    print(comparison)

    # Save comparison to file
    comparison_file = script_dir / "COMPARISON_REPORT.txt"
    with open(comparison_file, "w") as f:
        f.write(comparison)
    print(f"\n💾 Comparison report saved to: {comparison_file}")

    return 0


if __name__ == "__main__":
    exit(main())
