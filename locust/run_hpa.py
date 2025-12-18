import subprocess
import time
import os
import webbrowser
import sys
import threading
import json
import datetime
import shutil
import re

# Configuration
HOST = "http://136.114.153.163/" # Ensure this matches your Ingress IP
OUTPUT_DIR = "results_hpa" # Relative to script location
USER_CLASS = "AuthenticatedUser" # High CPU usage profile
POLL_INTERVAL = 5 # seconds
TEST_DURATION = 120 # seconds

USERS = 2000
SPAWN_RATE = 1

# Global list to store metrics
metrics_data = []
monitoring_active = True

def get_pod_metrics(app_label):
    """
    Parses `kubectl top pods -l app={app_label}` to get CPU for each individual pod.
    Returns a dict: { "pod_name": cpu_millicores, ... }
    """
    pod_cpu_map = {}
    try:
        # kubectl top pods -l app={app_label} --no-headers
        cmd = ["kubectl", "top", "pods", "-l", f"app={app_label}", "--no-headers"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                pod_name = parts[0]
                cpu_str = parts[1] # e.g. "493m" or "1" (cores)
                
                # Convert to millicores (integer)
                if cpu_str.endswith('m'):
                    cpu_val = int(cpu_str[:-1])
                else:
                    try:
                        cpu_val = int(float(cpu_str) * 1000)
                    except:
                        cpu_val = 0
                        
                pod_cpu_map[pod_name] = cpu_val
    except:
        pass
    return pod_cpu_map

def get_hpa_metrics(hpa_name):
    """
    Gets Replicas and CPU % for a given HPA.
    Returns: (replicas, cpu_percent)
    """
    current_replicas = 0
    hpa_cpu = 0
    try:
        hpa_cmd = ["kubectl", "get", "hpa", hpa_name, "-o", "json"]
        hpa_out = subprocess.check_output(hpa_cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        hpa_json = json.loads(hpa_out)
        current_replicas = hpa_json['status'].get('currentReplicas', 0)
        
        if 'currentMetrics' in hpa_json['status']:
            for metric in hpa_json['status']['currentMetrics']:
                if metric['type'] == 'Resource' and metric['resource']['name'] == 'cpu':
                    if 'current' in metric['resource'] and 'averageUtilization' in metric['resource']['current']:
                        hpa_cpu = metric['resource']['current']['averageUtilization']
    except:
        pass

    # Bug Fix: If replicas is 0, verify with direct pod count
    if current_replicas == 0:
        app_name = hpa_name.replace("-hpa", "").replace("heath-", "") # e.g. 'frontend' or 'backend'
        try:
            pod_count_cmd = ["kubectl", "get", "pods", "-l", f"app={app_name}", "--no-headers"]
            output = subprocess.check_output(pod_count_cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
            if output:
                current_replicas = len([line for line in output.split('\n') if line.strip()])
        except:
            pass

    return current_replicas, hpa_cpu

def get_deployment_metrics(deployment_name):
    """
    Gets Desired vs Ready replicas from Deployment.
    Returns: (desired, ready)
    """
    try:
        cmd = ["kubectl", "get", "deployment", deployment_name, "-o", "json"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        data = json.loads(out)
        desired = data['status'].get('replicas', 0) # Total pods created
        ready = data['status'].get('readyReplicas', 0) # Pods actually running & ready
        return desired, ready
    except:
        return 0, 0

def get_node_metrics():
    """
    Gets Total and Ready node counts from the cluster.
    Returns: (total, ready)
    """
    total = 0
    ready = 0
    try:
        cmd = ["kubectl", "get", "nodes", "--no-headers"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if output:
            lines = output.split('\n')
            total = len(lines)
            for line in lines:
                if "Ready" in line:
                    ready += 1
    except:
        pass
    return total, ready

def monitor_k8s_metrics(results_dir):
    """
    Background thread function to poll Kubernetes HPA and Pod metrics for both Backend and Frontend.
    """
    global monitoring_active
    print("   👀 Kubernetes Monitoring Started (Backend & Frontend)...")
    
    start_time = time.time()
    
    while monitoring_active:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = int(time.time() - start_time)
        
        # HPA Metrics (CPU target)
        _, be_hpa_cpu = get_hpa_metrics("heath-backend-hpa")
        _, fe_hpa_cpu = get_hpa_metrics("heath-frontend-hpa")

        # Deployment Metrics (True Replica Counts)
        be_desired, be_ready = get_deployment_metrics("heath-backend")
        fe_desired, fe_ready = get_deployment_metrics("heath-frontend")

        # Pod CPU Metrics
        be_pods = get_pod_metrics("backend")
        fe_pods = get_pod_metrics("frontend")

        # Node Metrics
        total_nodes, ready_nodes = get_node_metrics()

        # Store data point
        metrics_data.append({
            "time": timestamp,
            "elapsed": elapsed,
            "nodes": {
                "total": total_nodes,
                "ready": ready_nodes
            },
            "backend": {
                "desired_replicas": be_desired,
                "ready_replicas": be_ready,
                "hpa_cpu": be_hpa_cpu,
                "pods": be_pods
            },
            "frontend": {
                "desired_replicas": fe_desired,
                "ready_replicas": fe_ready,
                "hpa_cpu": fe_hpa_cpu,
                "pods": fe_pods
            }
        })
        
        time.sleep(POLL_INTERVAL)

def generate_k8s_report(results_dir):
    """
    Generates HTML report with 4 charts:
    1. Backend HPA
    2. Backend Pods
    3. Frontend HPA
    4. Frontend Pods
    """
    
    # helper to extract pod datasets
    def get_pod_datasets(data_key):
        all_names = set()
        for entry in metrics_data:
            all_names.update(entry[data_key]['pods'].keys())
        
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#E7E9ED', '#767676']
        
        for idx, name in enumerate(sorted(all_names)):
            points = []
            for entry in metrics_data:
                points.append(entry[data_key]['pods'].get(name, 0))
            
            datasets.append({
                "label": name,
                "data": points,
                "borderColor": colors[idx % len(colors)],
                "backgroundColor": colors[idx % len(colors)],
                "fill": False,
                "tension": 0.1
            })
        return datasets

    be_pod_datasets = get_pod_datasets('backend')
    fe_pod_datasets = get_pod_datasets('frontend')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>K8s Metrics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f4f4f4; }}
            .card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1, h2 {{ text-align: center; color: #333; }}
            .row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
            .col {{ flex: 1; min-width: 45%; }}
            canvas {{ max-height: 350px; }}
        </style>
    </head>
    <body>
        <h1>Kubernetes Full Stack Scaling Report</h1>
        
        <!-- BACKEND SECTION -->
        <div class="row">
            <div class="col card">
                <h2>Backend HPA (Replicas vs Avg CPU)</h2>
                <canvas id="beHpaChart"></canvas>
            </div>
            <div class="col card">
                <h2>Backend Pod CPU (millicores)</h2>
                <canvas id="bePodsChart"></canvas>
            </div>
        </div>

        <!-- FRONTEND SECTION -->
        <div class="row">
            <div class="col card">
                <h2>Frontend HPA (Replicas vs Avg CPU)</h2>
                <canvas id="feHpaChart"></canvas>
            </div>
            <div class="col card">
                <h2>Frontend Pod CPU (millicores)</h2>
                <canvas id="fePodsChart"></canvas>
            </div>
        </div>

        <!-- NODES SECTION -->
        <div class="row">
            <div class="col card">
                <h2>Data Nodes (Cluster Scaling)</h2>
                <canvas id="nodeChart"></canvas>
            </div>
        </div>

        <script>
            const rawData = {json.dumps(metrics_data)};
            const labels = rawData.map(d => d.time);
            
            const beDesired = rawData.map(d => d.backend.desired_replicas);
            const beReady = rawData.map(d => d.backend.ready_replicas);
            const beHpaCpu = rawData.map(d => d.backend.hpa_cpu);
            
            const feDesired = rawData.map(d => d.frontend.desired_replicas);
            const feReady = rawData.map(d => d.frontend.ready_replicas);
            const feHpaCpu = rawData.map(d => d.frontend.hpa_cpu);

            const totalNodes = rawData.map(d => d.nodes.total);
            const readyNodes = rawData.map(d => d.nodes.ready);

            const commonOptions = {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
            }};

            const hpaScales = {{
                y: {{
                    type: 'linear', display: true, position: 'left',
                    title: {{ display: true, text: 'Pod Count' }},
                    min: 0, suggestedMax: 5,
                    ticks: {{ stepSize: 1 }}  // INTEGERS ONLY
                }},
                y1: {{
                    type: 'linear', display: true, position: 'right',
                    title: {{ display: true, text: 'HPA CPU Target (%)' }},
                    grid: {{ drawOnChartArea: false }},
                    min: 0
                }}
            }};

            // --- Backend Charts ---
            new Chart(document.getElementById('beHpaChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Desired Replicas', data: beDesired, borderColor: '#36A2EB', borderDash: [5, 5], yAxisID: 'y', stepped: true }},
                        {{ label: 'Ready Replicas', data: beReady, borderColor: '#36A2EB', backgroundColor: 'rgba(54, 162, 235, 0.2)', yAxisID: 'y', stepped: true, fill: true }},
                        {{ label: 'Avg CPU %', data: beHpaCpu, borderColor: '#FF6384', yAxisID: 'y1', tension: 0.4 }}
                    ]
                }},
                options: {{ ...commonOptions, scales: hpaScales }}
            }});

            new Chart(document.getElementById('bePodsChart'), {{
                type: 'line',
                data: {{ labels: labels, datasets: {json.dumps(be_pod_datasets)} }},
                options: {{ ...commonOptions, plugins: {{ legend: {{ position: 'bottom' }} }} }}
            }});

            // --- Frontend Charts ---
            new Chart(document.getElementById('feHpaChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Desired Replicas', data: feDesired, borderColor: '#4BC0C0', borderDash: [5, 5], yAxisID: 'y', stepped: true }},
                        {{ label: 'Ready Replicas', data: feReady, borderColor: '#4BC0C0', backgroundColor: 'rgba(75, 192, 192, 0.2)', yAxisID: 'y', stepped: true, fill: true }},
                        {{ label: 'Avg CPU %', data: feHpaCpu, borderColor: '#FF9F40', yAxisID: 'y1', tension: 0.4 }}
                    ]
                }},
                options: {{ ...commonOptions, scales: hpaScales }}
            }});

            new Chart(document.getElementById('fePodsChart'), {{
                type: 'line',
                data: {{ labels: labels, datasets: {json.dumps(fe_pod_datasets)} }},
                options: {{ ...commonOptions, plugins: {{ legend: {{ position: 'bottom' }} }} }}
            }});

            // --- Node Chart ---
            new Chart(document.getElementById('nodeChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Total Nodes', data: totalNodes, borderColor: '#9966FF', borderDash: [5, 5], stepped: true }},
                        {{ label: 'Ready Nodes', data: readyNodes, borderColor: '#9966FF', backgroundColor: 'rgba(153, 102, 255, 0.2)', stepped: true, fill: true }}
                    ]
                }},
                options: {{
                    ...commonOptions,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Node Count' }},
                            ticks: {{ stepSize: 1 }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    report_path = os.path.join(results_dir, "k8s_metrics.html")
    with open(report_path, "w") as f:
        f.write(html_content)
    
    print(f"📊 Kubernetes Metrics Report generated: {report_path}")
    # try:
    #     webbrowser.open(f"file://{report_path}")
    # except:
    #     pass

def run_hpa_test():
    global monitoring_active
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    locustfile_path = os.path.join(script_dir, "locustfile.py")
    results_dir = os.path.join(script_dir, OUTPUT_DIR)
    
    print(f"\n🚀 Starting HPA Test: {USER_CLASS}")
    print("🎯 Target: Trigger CPU > 50% to scale from 1 -> N replicas")
    print(f"⏱️  Duration: {TEST_DURATION} seconds")
    
    os.makedirs(results_dir, exist_ok=True)
    html_report = os.path.join(results_dir, "locust_report.html")
    
    # Check locust
    locust_executable = "locust"
    try:
        if subprocess.call(["which", "locust"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            locust_executable = [sys.executable, "-m", "locust"]
        else:
            locust_executable = ["locust"]
    except Exception:
        locust_executable = [sys.executable, "-m", "locust"]

    # Start Monitoring
    monitor_thread = threading.Thread(target=monitor_k8s_metrics, args=(results_dir,))
    monitor_thread.daemon = True 
    monitor_thread.start()

    cmd = locust_executable + [
        "-f", locustfile_path,   
        USER_CLASS,
        "--host", HOST,
        "--autostart",           
        "--autoquit", str(TEST_DURATION),     
        "--users", str(USERS),         
        "--spawn-rate", str(SPAWN_RATE),
        "--html", html_report
    ]

    try:
        print("   ...Starting Locust Web UI...")
        print("   📊 Live Charts available at: http://localhost:8089")
        #try:
        #    webbrowser.open("http://localhost:8089")
        #except:
        #    pass

        subprocess.run(cmd, check=True)
        print("\n✅ Test Complete.")
        print(f"📊 Locust Report generated: {html_report}")
        
    except subprocess.CalledProcessError:
        print("\n⚠️ Test interrupted or failed.")
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")
    finally:
        monitoring_active = False
        monitor_thread.join() 
        generate_k8s_report(results_dir)

if __name__ == "__main__":
    run_hpa_test()