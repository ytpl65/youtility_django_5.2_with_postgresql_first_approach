# YOUTILITY3 Load Testing Suite

## Overview

This directory contains comprehensive load testing tools for YOUTILITY3 production validation. The testing suite includes:

- **Artillery.js** - Modern load testing with realistic user scenarios
- **Database Performance Testing** - PostgreSQL function and query performance
- **Health Check Load Testing** - Endpoint reliability under load
- **System Monitoring** - Resource usage tracking during tests

## Quick Start

### 1. Prerequisites

**System Requirements:**
- Python 3.8+
- Node.js 14+ (for Artillery.js)
- PostgreSQL client tools
- YOUTILITY3 application running

**Install Dependencies:**
```bash
# Install Node.js dependencies
npm install -g artillery

# Install Python dependencies  
pip3 install requests psycopg2-binary django pandas

# Install system monitoring tools (Ubuntu/Debian)
sudo apt-get install bc iostat sysstat
```

### 2. Start Your Application

Make sure YOUTILITY3 is running:
```bash
# In your YOUTILITY3 directory
python3 manage.py runserver 0.0.0.0:8000

# Or if using production server
# systemctl start youtility
```

### 3. Run Load Tests

**Full Test Suite (Recommended):**
```bash
cd testing/load_testing
./run_load_tests.sh http://localhost:8000
```

**Individual Tests:**
```bash
# Artillery load testing only
artillery run artillery_config.yml

# Database performance testing only
python3 database_performance_test.py

# Health check testing only
python3 health_check_load_test.py --url http://localhost:8000
```

### 4. View Results

Results are saved to `testing/load_testing/results/YYYYMMDD_HHMMSS/`:
- `load_test_report.html` - Comprehensive HTML report
- `artillery_report.html` - Artillery.js detailed results
- `system_metrics.csv` - System resource usage
- `load_test.log` - Complete test execution log

## Test Scenarios

### Artillery.js Load Testing

**Test Phases:**
1. **Warm-up** (60s) - 5 users/second
2. **Baseline** (300s) - 10 users/second  
3. **Normal Load** (300s) - 50 users/second
4. **Peak Load** (300s) - 100 users/second
5. **Stress Test** (180s) - 200 users/second
6. **Cool Down** (60s) - 5 users/second

**User Scenarios:**
- Health Check Monitoring (20%)
- User Login Flow (30%)
- Dashboard Navigation (25%)
- API Testing (15%)
- Form Submissions (10%)

### Database Performance Testing

**Tests Include:**
- PostgreSQL function performance (`check_rate_limit`, `cleanup_expired_sessions`, etc.)
- Materialized view query performance
- Concurrent database load testing
- Connection pool behavior analysis

**Performance Targets:**
- `check_rate_limit()`: <20ms average
- `cleanup_expired_sessions()`: <100ms average
- Materialized views: <5ms average
- Concurrent load: >50 queries/second

### Health Check Load Testing

**Endpoints Tested:**
- `/health/` - Basic health check
- `/ready/` - Readiness probe  
- `/alive/` - Liveness probe
- `/health/detailed/` - Detailed system status

**Performance Targets:**
- Response time: <100ms average
- Success rate: >99%
- Reliability under application load

## Configuration

### Artillery Configuration

Edit `artillery_config.yml` to customize:
```yaml
config:
  target: 'http://your-server:8000'
  phases:
    - duration: 300
      arrivalRate: 50
      name: "Custom Load"
```

### Database Test Configuration

Edit `database_performance_test.py` for custom tests:
```python
# Add custom database tests
test_functions = [
    {
        'name': 'custom_function',
        'query': "SELECT your_function(%s)",
        'params': ['test_param'],
        'target_ms': 30
    }
]
```

### System Monitoring

Monitoring collects metrics every 30 seconds:
- CPU usage percentage
- Memory usage (percentage and MB)
- Disk I/O operations
- Network traffic (RX/TX)
- Database connections

## Interpreting Results

### Success Criteria

**Load Testing:**
- ✅ 100 concurrent users with <500ms average response
- ✅ <1% error rate under normal load
- ✅ System resources within limits (CPU <70%, Memory <80%)

**Database Performance:**
- ✅ All PostgreSQL functions meet target response times
- ✅ >50 queries/second sustained throughput
- ✅ <5% error rate under concurrent load

**Health Checks:**
- ✅ <100ms response time under any load
- ✅ >99% success rate
- ✅ Reliable during application stress

### Common Issues

**High Response Times:**
- Check database query performance
- Review materialized view refresh frequency
- Verify adequate system resources

**High Error Rates:**
- Check application logs for exceptions
- Verify database connectivity
- Review rate limiting configuration

**Resource Exhaustion:**
- Increase memory allocation
- Optimize database queries
- Consider connection pooling adjustments

## Troubleshooting

### Test Setup Issues

**"Service not responding":**
```bash
# Check if application is running
curl http://localhost:8000/health/

# Check logs
tail -f /var/log/youtility/production.log

# Restart application
systemctl restart youtility
```

**Missing Dependencies:**
```bash
# Install all dependencies
./run_load_tests.sh --install-deps

# Or manually:
npm install -g artillery
pip3 install -r ../requirements.txt
```

### During Test Execution

**High Memory Usage:**
- Monitor with `htop` during tests
- Consider reducing concurrent users
- Check for memory leaks in application

**Database Connection Errors:**
- Verify PostgreSQL max_connections setting
- Check connection pool configuration
- Monitor `pg_stat_activity`

**Network Issues:**
- Verify firewall settings
- Check network bandwidth
- Monitor with `iftop` or `netstat`

## Advanced Usage

### Custom Load Scenarios

Create custom Artillery scenarios:
```yaml
scenarios:
  - name: "Custom API Testing"
    weight: 50
    flow:
      - post:
          url: "/api/custom/"
          json:
            test_data: "value"
      - think: 2
```

### Extended Database Testing

Add custom database tests:
```python
def test_custom_queries(self):
    # Your custom database testing logic
    pass
```

### CI/CD Integration

For automated testing:
```bash
# Quick validation test
./run_load_tests.sh --quick --url http://staging-server

# Full production validation  
./run_load_tests.sh --url http://production-server
```

## Performance Baselines

Based on development testing:

| Metric | Target | Good | Excellent |
|--------|--------|------|-----------|
| Response Time (avg) | <500ms | <300ms | <200ms |
| Response Time (95th) | <1000ms | <600ms | <400ms |
| Concurrent Users | 100 | 200 | 500+ |
| Error Rate | <1% | <0.5% | <0.1% |
| DB Query Time | <50ms | <25ms | <10ms |
| Health Check Time | <100ms | <50ms | <25ms |

## Support

For issues or questions:

1. **Check Logs**: Review `load_test.log` for detailed error information
2. **System Resources**: Monitor CPU, memory, and database during tests
3. **Application Health**: Verify health endpoints respond correctly
4. **Database Performance**: Check PostgreSQL logs and `pg_stat_statements`

## Files Description

- `artillery_config.yml` - Artillery.js load test configuration
- `database_performance_test.py` - Database performance testing script
- `health_check_load_test.py` - Health endpoint load testing script
- `run_load_tests.sh` - Main test runner script
- `README.md` - This documentation file

---

**Ready to test?** Run `./run_load_tests.sh` to start comprehensive load testing!