#!/usr/bin/env python
"""
Generate baseline performance report from metrics file.

This script parses baseline_metrics.txt and generates a comprehensive markdown
report with all performance metrics and optimization targets.
"""

import re
from datetime import datetime
from pathlib import Path


def parse_metrics_file(file_path: Path) -> dict:
    """Parse baseline metrics file into structured data."""
    metrics = {
        "query_counts": {},
        "response_times": {},
        "response_sizes": {},
        "database_connections": {},
        "cache_performance": {},
        "memory_usage": {},
        "task_performance": {},
    }

    with open(file_path) as f:
        content = f.read()

    # Parse query counts
    query_pattern = r"Test: (\w+)\nTotal Queries: (\d+)"
    for match in re.finditer(query_pattern, content):
        test_name, query_count = match.groups()
        metrics["query_counts"][test_name] = int(query_count)

    # Parse response times
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
        test_name, mean, min_time, max_time, stddev, p50, p95, p99 = match.groups()
        metrics["response_times"][test_name] = {
            "mean": float(mean),
            "min": float(min_time),
            "max": float(max_time),
            "stddev": float(stddev),
            "p50": float(p50),
            "p95": float(p95),
            "p99": float(p99),
        }

    # Parse response sizes
    size_pattern = (
        r"Response Size Test: (\w+)\n={80}\n"
        r"Uncompressed: (\d+) bytes \(([\d.]+) KB\)\n"
        r"Compressed \(gzip\): (\d+) bytes \(([\d.]+) KB\)\n"
        r"Compression ratio: ([\d.]+)%\n"
        r"Size reduction: ([\d.]+)% \((\d+) bytes saved\)"
    )
    for match in re.finditer(size_pattern, content):
        (
            test_name,
            uncomp_bytes,
            uncomp_kb,
            comp_bytes,
            comp_kb,
            ratio,
            reduction,
            saved,
        ) = match.groups()
        metrics["response_sizes"][test_name] = {
            "uncompressed_bytes": int(uncomp_bytes),
            "uncompressed_kb": float(uncomp_kb),
            "compressed_bytes": int(comp_bytes),
            "compressed_kb": float(comp_kb),
            "compression_ratio": float(ratio),
            "size_reduction": float(reduction),
            "bytes_saved": int(saved),
        }

    # Parse database connection info
    conn_pattern = r"Database Connection Test: (\w+)\n={80}\n(.*?)={80}"
    for match in re.finditer(conn_pattern, content, re.DOTALL):
        test_name, details = match.groups()
        metrics["database_connections"][test_name] = details.strip()

    # Parse cache performance
    cache_pattern = r"Cache Performance Test: (\w+)\n={80}\n(.*?)={80}"
    for match in re.finditer(cache_pattern, content, re.DOTALL):
        test_name, details = match.groups()
        metrics["cache_performance"][test_name] = details.strip()

    # Parse memory usage
    memory_pattern = (
        r"Memory Usage Test: (\w+)\n={80}\n"
        r"Number of samples: (\d+)\n"
        r"Max memory usage: ([\d.]+) MB\n"
        r"Average memory usage: ([\d.]+) MB\n"
        r"Min memory usage: ([\d.]+) MB\n"
        r"Memory range: ([\d.]+) MB"
    )
    for match in re.finditer(memory_pattern, content):
        test_name, samples, max_mem, avg_mem, min_mem, range_mem = match.groups()
        metrics["memory_usage"][test_name] = {
            "samples": int(samples),
            "max_mb": float(max_mem),
            "average_mb": float(avg_mem),
            "min_mb": float(min_mem),
            "range_mb": float(range_mem),
        }

    # Parse task performance
    task_pattern = r"Task Performance Test: (\w+)\n={80}\n(.*?)={80}"
    for match in re.finditer(task_pattern, content, re.DOTALL):
        test_name, details = match.groups()
        metrics["task_performance"][test_name] = details.strip()

    return metrics


def generate_markdown_report(metrics: dict) -> str:
    """Generate comprehensive markdown report from metrics."""
    report = []
    report.append("# Performance Testing Baseline Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(
        "This report provides baseline performance metrics for the School Menu application."
    )
    report.append(
        "Use these metrics to track optimization progress and identify performance bottlenecks."
    )
    report.append("")

    # Query Counts Section
    report.append("## 📊 Database Query Counts")
    report.append("")
    report.append("Number of database queries executed for each test scenario:")
    report.append("")
    report.append("| Test Scenario | Query Count | Target | Status |")
    report.append("|--------------|-------------|--------|--------|")
    for test_name, count in sorted(metrics["query_counts"].items()):
        # Set targets based on test type
        if "baseline" in test_name:
            target = "Baseline"
            status = "📝 Baseline"
        elif "optimized" in test_name:
            target = "≤ Baseline"
            status = (
                "✅ Optimized"
                if count
                <= metrics["query_counts"].get(
                    test_name.replace("optimized", "baseline"), count
                )
                else "⚠️ Review"
            )
        else:
            target = "< 5"
            status = "✅ Good" if count < 5 else "⚠️ High"
        report.append(f"| {test_name} | {count} | {target} | {status} |")
    report.append("")

    # Response Times Section
    report.append("## ⏱️ Response Times")
    report.append("")
    report.append("Response time percentiles for critical endpoints:")
    report.append("")
    report.append("| Test | Mean | p50 | p95 | p99 | Target (p95) | Status |")
    report.append("|------|------|-----|-----|-----|--------------|--------|")
    for test_name, times in sorted(metrics["response_times"].items()):
        target_p95 = 50.0  # Target p95 < 50ms
        status = "✅ Good" if times["p95"] < target_p95 else "⚠️ Slow"
        report.append(
            f"| {test_name} | {times['mean']:.2f}ms | {times['p50']:.2f}ms | "
            f"{times['p95']:.2f}ms | {times['p99']:.2f}ms | <{target_p95}ms | {status} |"
        )
    report.append("")
    report.append("**Optimization Targets:**")
    report.append("- p95 response time: < 50ms")
    report.append("- p99 response time: < 100ms")
    report.append("- Mean response time: < 20ms")
    report.append("")

    # Response Sizes Section
    report.append("## 📦 Response Sizes")
    report.append("")
    report.append("Compression effectiveness for different response types:")
    report.append("")
    report.append(
        "| Resource | Uncompressed | Compressed | Ratio | Reduction | Status |"
    )
    report.append(
        "|----------|--------------|------------|-------|-----------|--------|"
    )
    for test_name, sizes in sorted(metrics["response_sizes"].items()):
        # Target compression: >70% for HTML/CSS, >60% for JS
        target = 70.0 if "html" in test_name or "css" in test_name else 60.0
        status = "✅ Good" if sizes["size_reduction"] >= target else "⚠️ Review"
        report.append(
            f"| {test_name} | {sizes['uncompressed_kb']:.2f} KB | "
            f"{sizes['compressed_kb']:.2f} KB | {sizes['compression_ratio']:.1f}% | "
            f"{sizes['size_reduction']:.1f}% | {status} |"
        )
    report.append("")
    report.append("**Optimization Targets:**")
    report.append("- HTML/CSS compression: > 70%")
    report.append("- JavaScript compression: > 60%")
    report.append("- Total page size: < 100 KB (compressed)")
    report.append("")

    # Database Connections Section
    report.append("## 🔌 Database Connections")
    report.append("")
    for test_name, details in sorted(metrics["database_connections"].items()):
        report.append(f"### {test_name}")
        report.append("```")
        report.append(details)
        report.append("```")
        report.append("")
    report.append("**Optimization Targets:**")
    report.append("- Enable CONN_MAX_AGE for connection pooling")
    report.append("- Reuse connections across requests")
    report.append("- Monitor connection count in production")
    report.append("")

    # Cache Performance Section
    report.append("## 💾 Cache Performance")
    report.append("")
    for test_name, details in sorted(metrics["cache_performance"].items()):
        report.append(f"### {test_name}")
        report.append("```")
        report.append(details)
        report.append("```")
        report.append("")
    report.append("**Optimization Targets:**")
    report.append("- Cache hit rate: > 80%")
    report.append("- Cached response time: < 10ms")
    report.append("- Proper cache invalidation on updates")
    report.append("")

    # Memory Usage Section
    report.append("## 🧠 Memory Usage")
    report.append("")
    report.append("Memory consumption for different test scenarios:")
    report.append("")
    report.append(
        "| Test | Samples | Min (MB) | Avg (MB) | Max (MB) | Range (MB) | Status |"
    )
    report.append(
        "|------|---------|----------|----------|----------|------------|--------|"
    )
    for test_name, mem in sorted(metrics["memory_usage"].items()):
        target_max = 500.0  # 500 MB threshold
        status = "✅ Good" if mem["max_mb"] < target_max else "⚠️ High"
        report.append(
            f"| {test_name} | {mem['samples']} | {mem['min_mb']:.2f} | "
            f"{mem['average_mb']:.2f} | {mem['max_mb']:.2f} | {mem['range_mb']:.2f} | {status} |"
        )
    report.append("")
    report.append("**Optimization Targets:**")
    report.append("- Max memory usage: < 500 MB")
    report.append("- Memory growth: < 100 MB over 100 requests")
    report.append("- No memory leaks detected")
    report.append("")

    # Task Performance Section
    report.append("## 🔄 Background Task Performance")
    report.append("")
    for test_name, details in sorted(metrics["task_performance"].items()):
        report.append(f"### {test_name}")
        report.append("```")
        report.append(details)
        report.append("```")
        report.append("")
    report.append("**Optimization Targets:**")
    report.append("- Total queries for notifications: < 10")
    report.append("- Time per subscriber: < 1ms")
    report.append("- Eliminate N+1 query patterns")
    report.append("")

    # Summary Section
    report.append("## 📋 Summary & Next Steps")
    report.append("")
    report.append("### Key Findings")
    report.append("")

    # Analyze query counts
    high_query_tests = [
        name
        for name, count in metrics["query_counts"].items()
        if count > 5 and "baseline" in name
    ]
    if high_query_tests:
        report.append(
            f"- **High Query Counts:** {len(high_query_tests)} tests with >5 queries"
        )
        report.append(f"  - {', '.join(high_query_tests)}")
    else:
        report.append("- **Query Counts:** All tests within acceptable range")

    # Analyze response times
    slow_tests = [
        name for name, times in metrics["response_times"].items() if times["p95"] > 50
    ]
    if slow_tests:
        report.append(f"- **Slow Responses:** {len(slow_tests)} tests with p95 > 50ms")
        report.append(f"  - {', '.join(slow_tests)}")
    else:
        report.append("- **Response Times:** All tests meet p95 target")

    # Memory status
    max_memory = (
        max(mem["max_mb"] for mem in metrics["memory_usage"].values())
        if metrics["memory_usage"]
        else 0
    )
    report.append(
        f"- **Memory Usage:** Peak at {max_memory:.2f} MB (threshold: 500 MB)"
    )

    report.append("")
    report.append("### Recommended Optimizations")
    report.append("")
    report.append("1. **Query Optimization:**")
    report.append(
        "   - Use select_related() and prefetch_related() to reduce N+1 queries"
    )
    report.append("   - Add database indexes for frequently filtered fields")
    report.append("   - Consider query result caching for static data")
    report.append("")
    report.append("2. **Caching Strategy:**")
    report.append("   - Implement page-level caching for school lists")
    report.append("   - Cache menu data with proper invalidation")
    report.append("   - Use Redis for production caching")
    report.append("")
    report.append("3. **Database Connections:**")
    report.append("   - Enable CONN_MAX_AGE in production settings")
    report.append("   - Configure connection pooling for PostgreSQL")
    report.append("")
    report.append("4. **Response Optimization:**")
    report.append("   - Ensure gzip compression enabled in production")
    report.append("   - Minimize HTML payload size")
    report.append("   - Optimize static asset delivery")
    report.append("")
    report.append("5. **Background Tasks:**")
    report.append("   - Optimize notification queries with select_related()")
    report.append("   - Batch database operations")
    report.append("   - Monitor task queue performance")
    report.append("")

    return "\n".join(report)


def main():
    """Main entry point for baseline report generation."""
    script_dir = Path(__file__).parent
    metrics_file = script_dir / "baseline_metrics.txt"
    report_file = script_dir / "BASELINE_REPORT.md"

    if not metrics_file.exists():
        print(f"❌ Error: Metrics file not found: {metrics_file}")
        print("Run performance tests first to generate baseline metrics.")
        return 1

    print("📊 Parsing baseline metrics...")
    metrics = parse_metrics_file(metrics_file)

    print("📝 Generating markdown report...")
    report = generate_markdown_report(metrics)

    print(f"💾 Saving report to {report_file}...")
    with open(report_file, "w") as f:
        f.write(report)

    print("✅ Baseline report generated successfully!")
    print(f"📄 Report saved to: {report_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Query count tests: {len(metrics['query_counts'])}")
    print(f"Response time tests: {len(metrics['response_times'])}")
    print(f"Response size tests: {len(metrics['response_sizes'])}")
    print(f"Database connection tests: {len(metrics['database_connections'])}")
    print(f"Cache performance tests: {len(metrics['cache_performance'])}")
    print(f"Memory usage tests: {len(metrics['memory_usage'])}")
    print(f"Task performance tests: {len(metrics['task_performance'])}")

    return 0


if __name__ == "__main__":
    exit(main())
