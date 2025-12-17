import subprocess
import time
import os
import webbrowser
import sys

# Configuration
HOST = "http://136.114.153.163/" # Ensure this matches your Ingress IP
OUTPUT_DIR = "results_hpa" # Relative to script location
USER_CLASS = "AuthenticatedUser" # High CPU usage profile

def run_hpa_test():
    # Get absolute path of this script to find sibling files reliably
    script_dir = os.path.dirname(os.path.abspath(__file__))
    locustfile_path = os.path.join(script_dir, "locustfile.py")
    results_dir = os.path.join(script_dir, OUTPUT_DIR)
    
    print(f"\n🚀 Starting HPA Test: {USER_CLASS}")
    print("🎯 Target: Trigger CPU > 50% to scale from 1 -> N replicas")
    print("⏱️  Duration: 5 minutes (to allow stabilization)")
    
    os.makedirs(results_dir, exist_ok=True)
    csv_prefix = os.path.join(results_dir, "hpa_test")
    html_report = os.path.join(results_dir, "hpa_report.html")
    
    # Check if locust is installed and available
    locust_executable = "locust"
    try:
        if subprocess.call(["which", "locust"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            # Fallback to python -m locust if 'locust' command is not found
            locust_executable = [sys.executable, "-m", "locust"]
        else:
            locust_executable = ["locust"]
    except Exception:
         # Fallback for systems without 'which'
        locust_executable = [sys.executable, "-m", "locust"]

    # Run with Web UI enabled
    cmd = locust_executable + [
        "-f", locustfile_path,   # Use absolute path
        USER_CLASS,
        "--host", HOST,
        "--autostart",           # Start the test automatically
        "--autoquit", "300",     # Stop after 300 seconds (5m)
        "--users", "1000",         
        "--spawn-rate", "10",
        "--csv", csv_prefix,
        "--html", html_report
    ]

    try:
        print("   ...Starting Locust Web UI...")
        print("   📊 Live Charts available at: http://localhost:8089")
        print("   (Monitor HPA in another terminal with: kubectl get hpa -w)")
        
        # Try to open the browser automatically
        try:
            webbrowser.open("http://localhost:8089")
        except:
            pass

        subprocess.run(cmd, check=True)
        print("\n✅ Test Complete.")
        print(f"📊 Report generated: {html_report}")
    except subprocess.CalledProcessError:
        print("\n⚠️ Test interrupted or failed.")
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")

if __name__ == "__main__":
    run_hpa_test()
