import subprocess
import time
import csv
import datetime
import re

# --- Config ---
OUTPUT_FILE = "locust/experiment_results/k8s_metrics.csv"
NAMESPACE = "default"
LABEL_SELECTOR = "app=heath-backend" # Ensure this matches your deployment label
INTERVAL_SEC = 2

def get_metrics():
    try:
        # Count Pods
        pod_cmd = ["kubectl", "get", "pods", "-l", LABEL_SELECTOR, "-n", NAMESPACE, "--no-headers"]
        pod_output = subprocess.run(pod_cmd, capture_output=True, text=True)
        if pod_output.returncode != 0:
            pod_count = 0
        else:
            lines = pod_output.stdout.strip().split('\n')
            pod_count = len([l for l in lines if l.strip()])

        # Count Nodes and Get CPU
        # kubectl top nodes --no-headers
        # Output: NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%
        node_cmd = ["kubectl", "top", "nodes", "--no-headers"]
        node_output = subprocess.run(node_cmd, capture_output=True, text=True)
        
        node_count = 0
        total_cpu = 0
        
        if node_output.returncode == 0:
            lines = node_output.stdout.strip().split('\n')
            valid_lines = [l for l in lines if l.strip()]
            node_count = len(valid_lines)
            
            for line in valid_lines:
                parts = line.split()
                if len(parts) >= 3:
                    # parts[2] is CPU%, e.g., "6%"
                    cpu_val = parts[2].replace('%', '')
                    if cpu_val.isdigit():
                        total_cpu += int(cpu_val)
        
        # If top failed (e.g. metrics server not ready), try just counting nodes
        if node_count == 0 and node_output.returncode != 0:
             count_cmd = ["kubectl", "get", "nodes", "--no-headers"]
             count_out = subprocess.run(count_cmd, capture_output=True, text=True)
             if count_out.returncode == 0:
                 lines = count_out.stdout.strip().split('\n')
                 node_count = len([l for l in lines if l.strip()])

        avg_cpu = round(total_cpu / node_count, 2) if node_count > 0 else 0

        return pod_count, node_count, avg_cpu
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return 0, 0, 0

def main():
    print(f"📊 Monitoring Kubernetes (Pods: {LABEL_SELECTOR})...")
    print(f"💾 Saving to {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "readable_time", "pod_count", "node_count", "avg_node_cpu_percent"])
        
        try:
            while True:
                ts = time.time()
                readable = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                pods, nodes, cpu = get_metrics()
                
                writer.writerow([ts, readable, pods, nodes, cpu])
                f.flush() # Ensure data is written immediately
                
                print(f"\r[{readable}] Pods: {pods} | Nodes: {nodes} | Avg Node CPU: {cpu}%", end="")
                time.sleep(INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped.")

if __name__ == "__main__":
    main()
