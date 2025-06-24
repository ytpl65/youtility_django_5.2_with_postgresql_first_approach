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
