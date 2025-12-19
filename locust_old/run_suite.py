import subprocess
import time
import json
import csv
import os

# Configuration
HOST = "http://136.111.14.184"
DURATION = "2m"  # Duration for each test
USERS = 2000
SPAWN_RATE = 100
OUTPUT_DIR = "locust/results"

# Define the tests to run
# (UserClass, Description)
TESTS = [
    ("PublicUser", "1. Public Read/Network Test"),
    ("AuthenticatedUser", "2. Authentication & General Load"),
    ("SocialUser", "3. DB Concurrency (Social)"),
    ("JourneyUser", "4. Full User Journey")
]

def run_test(user_class, description):
    print(f"\n{'='*60}")
    print(f"Starting: {description}")
    print(f"User: {user_class} | Users: {USERS} | Duration: {DURATION}")
    print(f"{'='*60}")

    # Create output directory if not exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # CSV file prefix for this test
    csv_prefix = f"{OUTPUT_DIR}/{user_class}"
    
    # Construct command
    # --headless: Run without UI
    # --u: Number of users
    # --r: Spawn rate
    # --run-time: How long to run
    # --csv: Output results to CSV
    cmd = [
        "locust",
        "-f", "locust/locustfile.py",
        user_class,
        "--host", HOST,
        "--headless",
        "--users", str(USERS),
        "--spawn-rate", str(SPAWN_RATE),
        "--run-time", DURATION,
        "--csv", csv_prefix
    ]

    try:
        # Run the command
        subprocess.run(cmd, check=True)
        print(f"✅ Finished: {description}")
        return csv_prefix
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}")
        print(e)
        return None

def analyze_results(csv_prefix, description):
    # Locust generates several files, we care about '..._stats.csv'
    stats_file = f"{csv_prefix}_stats.csv"
    
    if not os.path.exists(stats_file):
        print(f"⚠️ No results found for {description}")
        return

    print(f"\n📊 RESULTS: {description}")
    print("-" * 60)
    print(f"{'Name':<40} | {'Reqs':<5} | {'Failures':<8} | {'Avg (ms)':<8} | {'95% (ms)':<8} | {'RPS':<5}")
    print("-" * 60)

    with open(stats_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only print the aggregate row or specific endpoints
            if row['Name'] == 'Aggregated':
                print(f"{'TOTAL':<40} | {row['Request Count']:<5} | {row['Failure Count']:<8} | {float(row['Average Response Time']):<8.2f} | {float(row['95%']):<8.2f} | {float(row['Requests/s']):<5.2f}")
            elif "http" not in row['Name']: # Skip static asset rows if any
                 print(f"{row['Name'][:40]:<40} | {row['Request Count']:<5} | {row['Failure Count']:<8} | {float(row['Average Response Time']):<8.2f} | {float(row['95%']):<8.2f} | {float(row['Requests/s']):<5.2f}")
    print("-" * 60)

def main():
    print("🚀 Starting Automated Performance Benchmark Suite")
    
    results = []
    
    for user_class, description in TESTS:
        csv_prefix = run_test(user_class, description)
        if csv_prefix:
            results.append((csv_prefix, description))
        
        # Cooldown between tests to let the server recover
        print("⏳ Cooling down for 10 seconds...")
        time.sleep(10)

    print("\n\n" + "="*60)
    print("📢 FINAL SUMMARY REPORT")
    print("="*60)
    
    for csv_prefix, description in results:
        analyze_results(csv_prefix, description)

if __name__ == "__main__":
    main()

