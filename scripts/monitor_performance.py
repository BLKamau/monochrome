#!/usr/bin/env python
"""
Performance monitoring script for development.
Checks database queries, response times, and memory usage.
"""

import os
import sys
import time
import psutil
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')
import django
django.setup()

from django.db import connection
from django.core.cache import cache


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def check_database_performance():
    """Check database query performance."""
    print(f"{Colors.BOLD}Database Performance:{Colors.ENDC}")
    
    # Test query performance
    start_time = time.time()
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users_user")
        user_count = cursor.fetchone()[0]
    query_time = (time.time() - start_time) * 1000
    
    print(f"  User count: {user_count}")
    print(f"  Query time: {query_time:.2f}ms")
    
    # Check for slow queries
    if query_time > 100:
        print(f"{Colors.YELLOW}  ⚠ Query time is high{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}  ✓ Query performance good{Colors.ENDC}")


def check_cache_performance():
    """Check cache performance."""
    print(f"\n{Colors.BOLD}Cache Performance:{Colors.ENDC}")
    
    # Test cache set/get
    test_key = 'perf_test_key'
    test_value = 'test_value' * 1000  # ~10KB
    
    # Set
    start_time = time.time()
    cache.set(test_key, test_value, 60)
    set_time = (time.time() - start_time) * 1000
    
    # Get
    start_time = time.time()
    retrieved = cache.get(test_key)
    get_time = (time.time() - start_time) * 1000
    
    # Clean up
    cache.delete(test_key)
    
    print(f"  Cache set time: {set_time:.2f}ms")
    print(f"  Cache get time: {get_time:.2f}ms")
    
    if set_time > 50 or get_time > 10:
        print(f"{Colors.YELLOW}  ⚠ Cache performance could be better{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}  ✓ Cache performance good{Colors.ENDC}")


def check_api_endpoints():
    """Test API endpoint response times."""
    print(f"\n{Colors.BOLD}API Endpoint Performance:{Colors.ENDC}")
    
    base_url = 'http://localhost:8000'
    endpoints = [
        ('/api/health/', 'GET'),
        ('/api/auth/login/', 'POST'),
        ('/api/docs/', 'GET'),
    ]
    
    for endpoint, method in endpoints:
        try:
            start_time = time.time()
            if method == 'GET':
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{base_url}{endpoint}", json={}, timeout=5)
            
            response_time = (time.time() - start_time) * 1000
            
            status_icon = "✓" if response.status_code < 400 else "✗"
            color = Colors.GREEN if response.status_code < 400 else Colors.RED
            
            print(f"  {endpoint}: {response_time:.2f}ms {color}{status_icon} {response.status_code}{Colors.ENDC}")
            
        except Exception as e:
            print(f"  {endpoint}: {Colors.RED}✗ Error: {str(e)}{Colors.ENDC}")


def check_system_resources():
    """Check system resource usage."""
    print(f"\n{Colors.BOLD}System Resources:{Colors.ENDC}")
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"  CPU Usage: {cpu_percent}%")
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"  Memory Usage: {memory.percent}% ({memory.used / 1024 / 1024 / 1024:.1f}GB / {memory.total / 1024 / 1024 / 1024:.1f}GB)")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    print(f"  Disk Usage: {disk.percent}% ({disk.used / 1024 / 1024 / 1024:.1f}GB / {disk.total / 1024 / 1024 / 1024:.1f}GB)")
    
    # Process info
    process = psutil.Process()
    print(f"\n  Django Process:")
    print(f"    Memory: {process.memory_info().rss / 1024 / 1024:.1f}MB")
    print(f"    Threads: {process.num_threads()}")


def main():
    print(f"\n{Colors.BOLD}=== Monochrome Performance Monitor ==={Colors.ENDC}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        check_database_performance()
        check_cache_performance()
        check_api_endpoints()
        check_system_resources()
        
        print(f"\n{Colors.GREEN}✓ Performance check completed{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error during performance check: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()