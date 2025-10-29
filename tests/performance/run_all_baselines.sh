#!/bin/bash

# Performance Testing Suite - Baseline Runner
# This script orchestrates all performance tests and generates comprehensive reports

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Output files
METRICS_FILE="$SCRIPT_DIR/baseline_metrics.txt"
REPORT_FILE="$SCRIPT_DIR/BASELINE_REPORT.md"

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Performance Testing Suite - Baseline Runner"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/manage.py" ]; then
    echo -e "${RED}Error: Cannot find manage.py. Please run this script from the project root.${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Clear old metrics file
if [ -f "$METRICS_FILE" ]; then
    echo -e "${YELLOW}⚠️  Removing old baseline metrics file...${NC}"
    rm "$METRICS_FILE"
fi

echo -e "${CYAN}📝 Metrics will be saved to: $METRICS_FILE${NC}"
echo -e "${CYAN}📄 Report will be saved to: $REPORT_FILE${NC}"
echo ""

# Function to run a test and append output
run_test() {
    local test_file=$1
    local test_name=$2

    echo "────────────────────────────────────────────────────────────────────────────────"
    echo -e "${BLUE}Running: $test_name${NC}"
    echo "────────────────────────────────────────────────────────────────────────────────"

    # Run the test and append output to metrics file
    ENVIRONMENT=test uv run pytest -v --tb=short --no-cov -m performance "$SCRIPT_DIR/$test_file" >> "$METRICS_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $test_name completed successfully${NC}"
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        exit 1
    fi
    echo ""
}

# Start timing
start_time=$(date +%s)

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 1: Database Query Performance"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_query_counts.py" "Query Count Tests"
run_test "test_duplicate_queries.py" "Duplicate Query Detection"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 2: Response Time Performance"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_response_times.py" "Response Time Benchmarks"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 3: Response Size Analysis"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_response_sizes.py" "Response Size Tests"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 4: Database Connection Management"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_database_connections.py" "Database Connection Tests"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 5: Cache Performance"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_cache_performance.py" "Cache Performance Tests"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 6: Memory Usage Analysis"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_memory_usage.py" "Memory Usage Tests"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 7: Background Task Performance"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

run_test "test_task_performance.py" "Background Task Tests"

# Calculate test duration
end_time=$(date +%s)
test_duration=$((end_time - start_time))

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Phase 8: Generating Baseline Report"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

if [ -f "$SCRIPT_DIR/generate_baseline_report.py" ]; then
    echo -e "${BLUE}📊 Generating baseline report...${NC}"
    python "$SCRIPT_DIR/generate_baseline_report.py"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Baseline report generated successfully${NC}"
    else
        echo -e "${RED}❌ Failed to generate baseline report${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Warning: generate_baseline_report.py not found${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Test Suite Complete!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ All performance tests completed successfully${NC}"
echo -e "⏱️  Total test duration: ${test_duration}s"
echo ""
echo "📁 Generated Files:"
echo "   - Metrics: $METRICS_FILE"
echo "   - Report:  $REPORT_FILE"
echo ""

# Ask about load tests
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Optional: Load Testing with Locust"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${YELLOW}Load tests simulate real-world traffic and take approximately 10 minutes.${NC}"
echo ""
read -p "Do you want to run load tests now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Starting load tests...${NC}"

    if [ -f "$SCRIPT_DIR/run_load_tests.sh" ]; then
        bash "$SCRIPT_DIR/run_load_tests.sh"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Load tests completed${NC}"
            echo ""
            echo "📁 Load test results:"
            echo "   - Results: $SCRIPT_DIR/results_*.csv"
            echo "   - HTML Report: $SCRIPT_DIR/locust_report.html"
        else
            echo -e "${RED}❌ Load tests failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Warning: run_load_tests.sh not found${NC}"
    fi
else
    echo -e "${CYAN}Skipping load tests.${NC}"
    echo ""
    echo "To run load tests later, execute:"
    echo "  bash tests/performance/run_load_tests.sh"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Next Steps"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "1. Review the baseline report:"
echo "   ${CYAN}cat $REPORT_FILE${NC}"
echo ""
echo "2. Identify performance bottlenecks and implement optimizations"
echo ""
echo "3. After optimization, run tests again and compare results:"
echo "   ${CYAN}bash tests/performance/run_all_baselines.sh${NC}"
echo "   ${CYAN}cp $METRICS_FILE $SCRIPT_DIR/optimized_metrics.txt${NC}"
echo "   ${CYAN}python $SCRIPT_DIR/compare_results.py${NC}"
echo ""
echo "4. For continuous monitoring, integrate these tests into your CI/CD pipeline"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}🎉 Performance testing suite completed!${NC}"
echo ""
