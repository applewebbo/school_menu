#!/bin/bash
#
# Load Testing Script for School Menu Application
#
# This script runs three different load test scenarios using Locust:
# 1. Light load: 10 users, 2 minutes
# 2. Medium load: 50 users, 3 minutes
# 3. Heavy load: 100 users, 5 minutes
#
# Usage:
#   ./tests/performance/run_load_tests.sh [scenario]
#
# Arguments:
#   scenario - Optional: 'light', 'medium', 'heavy', or 'all' (default: all)
#
# Examples:
#   ./tests/performance/run_load_tests.sh          # Run all scenarios
#   ./tests/performance/run_load_tests.sh light    # Run only light load test
#   ./tests/performance/run_load_tests.sh medium   # Run only medium load test
#   ./tests/performance/run_load_tests.sh heavy    # Run only heavy load test
#
# Results are saved to:
#   - tests/performance/load_test_results.txt (summary statistics)
#   - tests/performance/results_*.csv (detailed metrics for each scenario)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCUSTFILE="$SCRIPT_DIR/locustfile.py"
HOST="http://localhost:8000"
RESULTS_DIR="$SCRIPT_DIR"

# Ensure locustfile exists
if [ ! -f "$LOCUSTFILE" ]; then
    echo -e "${RED}Error: locustfile.py not found at $LOCUSTFILE${NC}"
    exit 1
fi

# Function to run a load test scenario
run_load_test() {
    local scenario_name=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local csv_prefix="${RESULTS_DIR}/results_${users}users"

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Running $scenario_name Load Test${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Users: $users"
    echo -e "Spawn rate: $spawn_rate users/sec"
    echo -e "Duration: $duration"
    echo -e "Results: ${csv_prefix}_*.csv"
    echo -e "${GREEN}========================================${NC}\n"

    # Run locust in headless mode
    locust \
        -f "$LOCUSTFILE" \
        --host="$HOST" \
        --users="$users" \
        --spawn-rate="$spawn_rate" \
        --run-time="$duration" \
        --headless \
        --csv="$csv_prefix" \
        --html="${csv_prefix}_report.html"

    echo -e "\n${GREEN}$scenario_name load test completed!${NC}\n"
}

# Function to display usage
usage() {
    echo "Usage: $0 [scenario]"
    echo ""
    echo "Arguments:"
    echo "  scenario - Optional: 'light', 'medium', 'heavy', or 'all' (default: all)"
    echo ""
    echo "Examples:"
    echo "  $0          # Run all scenarios"
    echo "  $0 light    # Run only light load test"
    echo "  $0 medium   # Run only medium load test"
    echo "  $0 heavy    # Run only heavy load test"
    exit 1
}

# Main execution
main() {
    local scenario=${1:-all}

    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}School Menu Load Testing Suite${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo -e "Host: $HOST"
    echo -e "Locustfile: $LOCUSTFILE"
    echo -e "Results directory: $RESULTS_DIR"
    echo -e "${YELLOW}========================================${NC}\n"

    # Check if server is running
    if ! curl -s "$HOST" > /dev/null 2>&1; then
        echo -e "${RED}Warning: Server at $HOST may not be running${NC}"
        echo -e "${YELLOW}Please ensure the development server is running before proceeding${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    case $scenario in
        light)
            run_load_test "Light" 10 2 "2m"
            ;;
        medium)
            run_load_test "Medium" 50 5 "3m"
            ;;
        heavy)
            run_load_test "Heavy" 100 10 "5m"
            ;;
        all)
            run_load_test "Light" 10 2 "2m"
            echo -e "\n${YELLOW}Waiting 30 seconds before next test...${NC}\n"
            sleep 30

            run_load_test "Medium" 50 5 "3m"
            echo -e "\n${YELLOW}Waiting 30 seconds before next test...${NC}\n"
            sleep 30

            run_load_test "Heavy" 100 10 "5m"
            ;;
        help|-h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown scenario '$scenario'${NC}"
            usage
            ;;
    esac

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}All load tests completed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Results saved to:"
    echo -e "  - ${RESULTS_DIR}/load_test_results.txt"
    echo -e "  - ${RESULTS_DIR}/results_*users_*.csv"
    echo -e "  - ${RESULTS_DIR}/results_*users_report.html"
    echo -e "${GREEN}========================================${NC}\n"
}

# Parse arguments and run
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    usage
fi

main "$@"
