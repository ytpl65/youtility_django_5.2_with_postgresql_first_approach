#!/bin/bash
# YOUTILITY3 Load Testing Suite Runner
# Comprehensive load testing for production validation

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$TEST_DIR/results/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$RESULTS_DIR/load_test.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to check if service is running
check_service() {
    local url="$1"
    local max_attempts=30
    local attempt=1
    
    log "${BLUE}🔍 Checking if service is running at $url...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url/health/" > /dev/null 2>&1; then
            log "${GREEN}✅ Service is running and healthy${NC}"
            return 0
        fi
        
        log "   Attempt $attempt/$max_attempts - waiting for service..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "${RED}❌ Service not responding after $max_attempts attempts${NC}"
    return 1
}

# Function to install dependencies
install_dependencies() {
    log "${BLUE}📦 Installing test dependencies...${NC}"
    
    # Check if Artillery is installed
    if ! command -v artillery &> /dev/null; then
        log "   Installing Artillery.js..."
        npm install -g artillery
    else
        log "   ✅ Artillery.js already installed"
    fi
    
    # Check Python dependencies
    if ! python3 -c "import requests" &> /dev/null; then
        log "   Installing Python requests..."
        pip3 install requests
    else
        log "   ✅ Python requests already installed"
    fi
    
    # Check for other Python dependencies
    for package in psycopg2-binary django; do
        if ! python3 -c "import $package" &> /dev/null 2>&1; then
            log "   Installing Python $package..."
            pip3 install $package
        else
            log "   ✅ Python $package already installed"
        fi
    done
}

# Function to run Artillery load tests
run_artillery_tests() {
    log "\n${BLUE}🚀 Running Artillery.js Load Tests...${NC}"
    
    cd "$TEST_DIR"
    
    # Update Artillery config with correct URL
    sed "s|target: 'http://localhost:8000'|target: '$BASE_URL'|g" artillery_config.yml > "$RESULTS_DIR/artillery_config.yml"
    
    # Run Artillery test
    log "   Starting Artillery load test..."
    if artillery run "$RESULTS_DIR/artillery_config.yml" --output "$RESULTS_DIR/artillery_results.json" 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✅ Artillery tests completed successfully${NC}"
        
        # Generate Artillery report
        if [ -f "$RESULTS_DIR/artillery_results.json" ]; then
            artillery report "$RESULTS_DIR/artillery_results.json" --output "$RESULTS_DIR/artillery_report.html"
            log "   📊 Artillery report generated: artillery_report.html"
        fi
    else
        log "${RED}❌ Artillery tests failed${NC}"
        return 1
    fi
}

# Function to run database performance tests
run_database_tests() {
    log "\n${BLUE}🗄️ Running Database Performance Tests...${NC}"
    
    cd "$TEST_DIR"
    
    # Set Django settings module
    export DJANGO_SETTINGS_MODULE=intelliwiz_config.settings
    
    if python3 database_performance_test.py 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✅ Database tests completed successfully${NC}"
        
        # Move result files to results directory
        mv database_performance_results_*.json "$RESULTS_DIR/" 2>/dev/null || true
    else
        log "${RED}❌ Database tests failed${NC}"
        return 1
    fi
}

# Function to run health check tests
run_health_check_tests() {
    log "\n${BLUE}🏥 Running Health Check Load Tests...${NC}"
    
    cd "$TEST_DIR"
    
    if python3 health_check_load_test.py --url "$BASE_URL" 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✅ Health check tests completed successfully${NC}"
        
        # Move result files to results directory
        mv health_check_load_test_results_*.json "$RESULTS_DIR/" 2>/dev/null || true
    else
        log "${RED}❌ Health check tests failed${NC}"
        return 1
    fi
}

# Function to run system monitoring
run_system_monitoring() {
    log "\n${BLUE}📊 Starting System Monitoring...${NC}"
    
    # Create system monitoring script
    cat > "$RESULTS_DIR/monitor_system.sh" << 'EOF'
#!/bin/bash
LOG_FILE="$1"
DURATION="$2"

echo "Timestamp,CPU%,Memory%,MemoryMB,DiskIO,NetworkRX,NetworkTX,DBConnections" > "$LOG_FILE"

start_time=$(date +%s)
end_time=$((start_time + DURATION))

while [ $(date +%s) -lt $end_time ]; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # CPU usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | sed 's/,//')
    
    # Memory usage
    memory_info=$(free -m | grep "Mem:")
    memory_total=$(echo $memory_info | awk '{print $2}')
    memory_used=$(echo $memory_info | awk '{print $3}')
    memory_percent=$(echo "scale=2; $memory_used * 100 / $memory_total" | bc 2>/dev/null || echo "0")
    
    # Disk I/O (simplified)
    disk_io=$(iostat -x 1 1 2>/dev/null | grep "sda\|nvme" | head -1 | awk '{print $4+$5}' || echo "0")
    
    # Network I/O (simplified)
    network_stats=$(cat /proc/net/dev | grep -E "eth0|ens|enp" | head -1)
    if [ -n "$network_stats" ]; then
        network_rx=$(echo $network_stats | awk '{print $2}')
        network_tx=$(echo $network_stats | awk '{print $10}')
    else
        network_rx="0"
        network_tx="0"
    fi
    
    # Database connections (if PostgreSQL is accessible)
    db_connections=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ' || echo "0")
    
    echo "$timestamp,$cpu_usage,$memory_percent,$memory_used,$disk_io,$network_rx,$network_tx,$db_connections" >> "$LOG_FILE"
    
    sleep 30
done
EOF
    
    chmod +x "$RESULTS_DIR/monitor_system.sh"
    
    # Start monitoring in background
    "$RESULTS_DIR/monitor_system.sh" "$RESULTS_DIR/system_metrics.csv" 3600 &
    MONITOR_PID=$!
    
    log "   📈 System monitoring started (PID: $MONITOR_PID)"
    echo $MONITOR_PID > "$RESULTS_DIR/monitor.pid"
}

# Function to stop system monitoring
stop_system_monitoring() {
    if [ -f "$RESULTS_DIR/monitor.pid" ]; then
        MONITOR_PID=$(cat "$RESULTS_DIR/monitor.pid")
        if kill -0 $MONITOR_PID 2>/dev/null; then
            log "${BLUE}📊 Stopping system monitoring...${NC}"
            kill $MONITOR_PID
            wait $MONITOR_PID 2>/dev/null || true
            rm "$RESULTS_DIR/monitor.pid"
            
            # Generate system monitoring report
            if [ -f "$RESULTS_DIR/system_metrics.csv" ]; then
                python3 << EOF
import pandas as pd
import sys

try:
    df = pd.read_csv('$RESULTS_DIR/system_metrics.csv')
    
    print("\n📊 System Resource Summary:")
    print(f"Average CPU Usage: {df['CPU%'].mean():.2f}%")
    print(f"Peak CPU Usage: {df['CPU%'].max():.2f}%")
    print(f"Average Memory Usage: {df['Memory%'].mean():.2f}%")
    print(f"Peak Memory Usage: {df['Memory%'].max():.2f}%")
    print(f"Average DB Connections: {df['DBConnections'].mean():.0f}")
    print(f"Peak DB Connections: {df['DBConnections'].max():.0f}")
    
    # Save summary
    summary = {
        'avg_cpu': float(df['CPU%'].mean()),
        'peak_cpu': float(df['CPU%'].max()),
        'avg_memory': float(df['Memory%'].mean()),
        'peak_memory': float(df['Memory%'].max()),
        'avg_db_connections': float(df['DBConnections'].mean()),
        'peak_db_connections': float(df['DBConnections'].max())
    }
    
    import json
    with open('$RESULTS_DIR/system_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
        
except Exception as e:
    print(f"Error generating system summary: {e}")
EOF
            fi
        fi
    fi
}

# Function to generate comprehensive report
generate_final_report() {
    log "\n${BLUE}📋 Generating Final Report...${NC}"
    
    # Create HTML report
    cat > "$RESULTS_DIR/load_test_report.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>YOUTILITY3 Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .error { color: #dc3545; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 3px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 YOUTILITY3 Load Test Report</h1>
        <p><strong>Test Date:</strong> $(date)</p>
        <p><strong>Target URL:</strong> BASE_URL_PLACEHOLDER</p>
        <p><strong>Test Duration:</strong> ~60 minutes</p>
    </div>
    
    <div class="section">
        <h2>📊 Test Summary</h2>
        <div class="metric">
            <strong>Artillery Load Tests:</strong>
            <span id="artillery-status">ARTILLERY_STATUS_PLACEHOLDER</span>
        </div>
        <div class="metric">
            <strong>Database Performance:</strong>
            <span id="db-status">DB_STATUS_PLACEHOLDER</span>
        </div>
        <div class="metric">
            <strong>Health Check Tests:</strong>
            <span id="health-status">HEALTH_STATUS_PLACEHOLDER</span>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Key Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Target</th><th>Actual</th><th>Status</th></tr>
            <tr><td>Concurrent Users</td><td>100</td><td>CONCURRENT_USERS_PLACEHOLDER</td><td>STATUS_PLACEHOLDER</td></tr>
            <tr><td>Average Response Time</td><td>&lt;500ms</td><td>AVG_RESPONSE_PLACEHOLDER</td><td>STATUS_PLACEHOLDER</td></tr>
            <tr><td>95th Percentile</td><td>&lt;1000ms</td><td>P95_RESPONSE_PLACEHOLDER</td><td>STATUS_PLACEHOLDER</td></tr>
            <tr><td>Error Rate</td><td>&lt;1%</td><td>ERROR_RATE_PLACEHOLDER</td><td>STATUS_PLACEHOLDER</td></tr>
            <tr><td>Health Check Response</td><td>&lt;100ms</td><td>HEALTH_RESPONSE_PLACEHOLDER</td><td>STATUS_PLACEHOLDER</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>📁 Detailed Reports</h2>
        <ul>
            <li><a href="artillery_report.html">Artillery.js Load Test Report</a></li>
            <li><a href="system_metrics.csv">System Resource Metrics</a></li>
            <li><a href="load_test.log">Complete Test Log</a></li>
        </ul>
    </div>
</body>
</html>
EOF
    
    # Replace placeholders in HTML report
    sed -i "s/BASE_URL_PLACEHOLDER/$BASE_URL/g" "$RESULTS_DIR/load_test_report.html"
    
    log "${GREEN}✅ Final report generated: load_test_report.html${NC}"
}

# Main execution function
main() {
    log "${BLUE}🚀 YOUTILITY3 Load Testing Suite${NC}"
    log "${BLUE}===============================${NC}"
    log "📅 Started at: $(date)"
    log "🎯 Target URL: $BASE_URL"
    log "📁 Results will be saved to: $RESULTS_DIR"
    
    # Check if service is running
    if ! check_service "$BASE_URL"; then
        log "${RED}❌ Cannot proceed - service is not running${NC}"
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Start system monitoring
    run_system_monitoring
    
    # Run tests
    local test_results=0
    
    # Run Artillery tests
    if run_artillery_tests; then
        log "${GREEN}✅ Artillery tests passed${NC}"
    else
        log "${YELLOW}⚠️  Artillery tests had issues${NC}"
        test_results=$((test_results + 1))
    fi
    
    # Run database tests
    if run_database_tests; then
        log "${GREEN}✅ Database tests passed${NC}"
    else
        log "${YELLOW}⚠️  Database tests had issues${NC}"
        test_results=$((test_results + 1))
    fi
    
    # Run health check tests
    if run_health_check_tests; then
        log "${GREEN}✅ Health check tests passed${NC}"
    else
        log "${YELLOW}⚠️  Health check tests had issues${NC}"
        test_results=$((test_results + 1))
    fi
    
    # Stop monitoring
    stop_system_monitoring
    
    # Generate final report
    generate_final_report
    
    # Final summary
    log "\n${BLUE}🎉 Load Testing Complete!${NC}"
    log "📁 Results directory: $RESULTS_DIR"
    log "📊 Open load_test_report.html for detailed results"
    
    if [ $test_results -eq 0 ]; then
        log "${GREEN}✅ All tests completed successfully!${NC}"
        log "${GREEN}🚀 System appears ready for production load${NC}"
        exit 0
    else
        log "${YELLOW}⚠️  $test_results test suite(s) had issues${NC}"
        log "${YELLOW}📋 Review individual test results for details${NC}"
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    log "\n${YELLOW}⚠️  Load testing interrupted${NC}"
    stop_system_monitoring
    log "📁 Partial results saved to: $RESULTS_DIR"
    exit 1
}

trap cleanup INT TERM

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    log "${YELLOW}⚠️  Warning: Running as root is not recommended${NC}"
fi

# Run main function
main "$@"