import subprocess
import time
import json
import csv
import os
import sys

# Configuration
HOST = "http://34.31.212.244"
OUTPUT_DIR = "locust/results"

# Load Levels to Test
LOAD_LEVELS = [
    # (Users, Spawn Rate, Duration, Description)
    (10, 2, "30s", "Tiny Load"),
    (50, 5, "30s", "Low Load"),
    (100, 10, "30s", "Mild Load"),
    (200, 20, "45s", "Medium Load"),
    (500, 30, "45s", "High Load"),
    (1000, 50, "1m", "Stress Load")
]

# Tests to run
TEST_PROFILES = [
    ("PublicUser", "Public Read/Network"),
    ("AuthenticatedUser", "Authentication & CPU"),
    ("SocialUser", "DB Concurrency"),
    ("JourneyUser", "Full User Journey")
]

def run_test(user_class, users, spawn_rate, duration, desc):
    print(f"\n🚀 Running {user_class} | {desc} | {users} Users | {spawn_rate} Spawn/s")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_prefix = f"{OUTPUT_DIR}/{user_class}_{users}u"
    
    cmd = [
        "locust",
        "-f", "locust/locustfile.py",
        user_class,
        "--host", HOST,
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--csv", csv_prefix
    ]

    try:
        # Capture output to avoid cluttering the screen
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return csv_prefix
    except subprocess.CalledProcessError:
        print(f"⚠️ Test failed or had high error rate: {user_class} with {users} users")
        return csv_prefix # Still try to read results if created

def get_stats(csv_prefix):
    stats_file = f"{csv_prefix}_stats.csv"
    if not os.path.exists(stats_file):
        return None
        
    try:
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Name'] == 'Aggregated':
                    return {
                        'reqs': int(row['Request Count']),
                        'fails': int(row['Failure Count']),
                        'avg_ms': float(row['Average Response Time']),
                        'p95_ms': float(row['95%']),
                        'rps': float(row['Requests/s'])
                    }
    except:
        return None
    return None

def print_pretty_table(results):
    # Header
    print("\n" + "="*105)
    print(f"{'User Profile':<20} | {'Load':<12} | {'Users':<6} | {'RPS':<8} | {'Avg (ms)':<9} | {'95% (ms)':<9} | {'Fail %':<7} | {'Status'}")
    print("="*105)

    for res in results:
        profile = res['profile']
        load_desc = res['load']
        users = res['users']
        stats = res['stats']
        
        if not stats:
            print(f"{profile:<20} | {load_desc:<12} | {users:<6} | {'N/A':<8} | {'N/A':<9} | {'N/A':<9} | {'N/A':<7} | ❌ Failed")
            continue

        fail_pct = (stats['fails'] / stats['reqs'] * 100) if stats['reqs'] > 0 else 0
        
        # Determine status
        status = "✅ Pass"
        if fail_pct > 1: status = "⚠️ Errors"
        if stats['avg_ms'] > 2000: status = "🐢 Slow"
        if fail_pct > 20: status = "🔥 Crash"

        print(f"{profile:<20} | {load_desc:<12} | {users:<6} | {stats['rps']:<8.1f} | {stats['avg_ms']:<9.0f} | {stats['p95_ms']:<9.0f} | {fail_pct:<7.1f} | {status}")
        
    print("="*105 + "\n")

def main():
    print("🧪 Starting Progressive Load Test Suite...")
    print("This will take about 10-15 minutes to test all combinations.")
    
    all_results = []

    for profile_class, profile_name in TEST_PROFILES:
        print(f"\nTesting Profile: {profile_name}")
        
        for users, spawn, duration, load_desc in LOAD_LEVELS:
            csv_prefix = run_test(profile_class, users, spawn, duration, load_desc)
            stats = get_stats(csv_prefix)

            # Print immediate feedback
            if stats:
                fail_pct = (stats['fails'] / stats['reqs'] * 100) if stats['reqs'] > 0 else 0
                status = "✅ Pass"
                if fail_pct > 1: status = "⚠️ Errors"
                if stats['avg_ms'] > 2000: status = "🐢 Slow"
                if fail_pct > 20: status = "🔥 Crash"
                print(f"   👉 {stats['rps']:.1f} RPS | {stats['avg_ms']:.0f}ms Avg | {fail_pct:.1f}% Fail | {status}")
            else:
                print(f"   👉 ❌ Failed to collect stats")
            
            all_results.append({
                'profile': profile_name,
                'load': load_desc,
                'users': users,
                'stats': stats
            })
            
            # Brief cooldown
            time.sleep(5)

    print("\nProcessing Results...")
    print_pretty_table(all_results)

if __name__ == "__main__":
    main()

