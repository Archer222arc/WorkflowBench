#!/usr/bin/env python3
"""
Diagnose API Hang Issue - 5.3 Test Process Stalling
====================================================

Issue: All 32 test processes stuck at "Executing workflow with 3 steps"
- No CPU usage (0%)
- 472 CLOSE_WAIT TCP connections
- No log updates for 15+ minutes
- Database not updated for 6+ hours

Diagnosis: API calls hanging indefinitely
"""

import subprocess
import json
import time
from datetime import datetime
import psutil
import socket

def diagnose_stuck_processes():
    """Diagnose why test processes are stuck"""
    
    print("=" * 60)
    print("5.3 Test Process Stalling Diagnosis")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    
    # 1. Count stuck processes
    ps_output = subprocess.run(
        ["ps", "aux"], 
        capture_output=True, 
        text=True
    ).stdout
    
    python_processes = [line for line in ps_output.split('\n') 
                       if 'python' in line and 'smart_batch' in line]
    
    print(f"\n1. Stuck Processes: {len(python_processes)}")
    for proc in python_processes[:3]:
        parts = proc.split()
        pid = parts[1]
        cpu = parts[2]
        mem = parts[3]
        start = parts[8]
        print(f"   PID {pid}: CPU={cpu}%, MEM={mem}%, START={start}")
    
    # 2. Check network connections
    netstat_output = subprocess.run(
        ["netstat", "-an"],
        capture_output=True,
        text=True
    ).stdout
    
    close_wait = [line for line in netstat_output.split('\n') 
                  if 'CLOSE_WAIT' in line]
    
    print(f"\n2. CLOSE_WAIT Connections: {len(close_wait)}")
    
    # Group by remote host
    remote_hosts = {}
    for conn in close_wait:
        parts = conn.split()
        if len(parts) >= 5:
            remote = parts[4].split('.')[0:4]  # Get IP part
            remote_ip = '.'.join(remote[:4]) if len(remote) >= 4 else 'unknown'
            remote_hosts[remote_ip] = remote_hosts.get(remote_ip, 0) + 1
    
    print("   Top remote hosts with CLOSE_WAIT:")
    for host, count in sorted(remote_hosts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     {host}: {count} connections")
    
    # 3. Check last log activity
    import glob
    log_files = glob.glob("logs/batch_test_*.log")
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    if log_files:
        latest_log = log_files[0]
        mtime = os.path.getmtime(latest_log)
        time_ago = (time.time() - mtime) / 60
        print(f"\n3. Latest Log: {os.path.basename(latest_log)}")
        print(f"   Last modified: {time_ago:.1f} minutes ago")
        
        # Check last few lines
        with open(latest_log, 'r') as f:
            lines = f.readlines()
            if lines:
                last_timestamp = None
                for line in reversed(lines):
                    if line.strip() and line[0].isdigit():
                        last_timestamp = line.split(' - ')[0]
                        break
                if last_timestamp:
                    print(f"   Last log entry: {last_timestamp}")
    
    # 4. Check database update
    db_path = "pilot_bench_cumulative_results/master_database.json"
    if os.path.exists(db_path):
        mtime = os.path.getmtime(db_path)
        time_ago = (time.time() - mtime) / 3600
        print(f"\n4. Database last updated: {time_ago:.1f} hours ago")
    
    # 5. Diagnosis
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    
    if len(python_processes) > 0 and len(close_wait) > 100:
        print("❌ CRITICAL: API calls are hanging indefinitely")
        print("   - All processes stuck with 0% CPU")
        print("   - Hundreds of CLOSE_WAIT connections")
        print("   - Azure API endpoints not responding properly")
        print("\nROOT CAUSE:")
        print("   The API client is not handling timeouts correctly.")
        print("   When Azure API doesn't respond, the connection enters")
        print("   CLOSE_WAIT state but the Python process waits forever.")
        print("\nRECOMMENDED FIX:")
        print("   1. Add proper timeout to Azure API calls")
        print("   2. Implement connection pooling with max lifetime")
        print("   3. Add retry logic with exponential backoff")
        print("   4. Kill and restart stuck processes")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    import os
    import sys
    
    # Make sure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    diagnose_stuck_processes()