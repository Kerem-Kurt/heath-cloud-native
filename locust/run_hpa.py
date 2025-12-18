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
db_pool_data = []  # DB Connection Pool metrics
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

def fetch_recent_db_pool_logs(since_seconds=10):
    """
    Fetches recent backend logs and parses HikariCP connection pool stats.
    Same approach as visualize_db_bottleneck.py but for recent logs only.
    Returns: list of parsed metrics dicts
    """
    try:
        # Fetch recent logs (similar to visualize_db_bottleneck.py)
        cmd = ["kubectl", "logs", "-l", "app=backend", f"--since={since_seconds}s", "--timestamps"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
        
        data_points = []
        ts_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')
        
        for line in output.split('\n'):
            # Same parsing logic as visualize_db_bottleneck.py
            if "HikariPool" in line and "Connection is not available" in line and "waiting=" in line:
                ts_match = ts_pattern.search(line)
                if not ts_match:
                    continue
                
                try:
                    # Extract metrics: (total=10, active=10, idle=0, waiting=173)
                    stats_part = line[line.rfind('(')+1 : line.rfind(')')]
                    parts = [p.strip() for p in stats_part.split(',')]
                    metrics = {}
                    for p in parts:
                        if '=' in p:
                            k, v = p.split('=')
                            metrics[k] = int(v)
                    
                    data_points.append({
                        "total": metrics.get('total', 10),
                        "active": metrics.get('active', 0),
                        "idle": metrics.get('idle', 0),
                        "waiting": metrics.get('waiting', 0)
                    })
                except:
                    pass
        
        return data_points
    except Exception as e:
        return []

def poll_db_pool_metrics():
    """
    Polls DB pool metrics by fetching recent logs (same approach as visualize_db_bottleneck.py).
    Returns: dict with total, active, idle, waiting
    """
    # Fetch recent logs and parse them
    recent_data = fetch_recent_db_pool_logs(since_seconds=POLL_INTERVAL + 2)
    
    if recent_data:
        # Aggregate: use max waiting from recent period (captures spikes)
        max_waiting = max(d['waiting'] for d in recent_data)
        max_active = max(d['active'] for d in recent_data)
        # Use the last data point but with max waiting
        result = recent_data[-1].copy()
        result['waiting'] = max_waiting
        result['active'] = max_active
        return result
    
    # No exhaustion events in logs - pool is healthy
    # Return zeros to indicate no bottleneck
    return {
        "total": 10,  # Default HikariCP pool size
        "active": 0,
        "idle": 10,
        "waiting": 0
    }

def monitor_k8s_metrics(results_dir):
    """
    Background thread function to poll Kubernetes HPA and Pod metrics for both Backend and Frontend.
    Also polls DB connection pool metrics at each interval by fetching recent logs.
    """
    global monitoring_active, db_pool_data
    print("   👀 Kubernetes Monitoring Started (Backend, Frontend & DB Pool)...")
    
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
        
        # DB Connection Pool Metrics (polled at same interval)
        db_metrics = poll_db_pool_metrics()
        db_pool_data.append({
            "time": timestamp,
            "elapsed": elapsed,
            "total": db_metrics.get('total', 10),
            "active": db_metrics.get('active', 0),
            "idle": db_metrics.get('idle', 0),
            "waiting": db_metrics.get('waiting', 0)
        })

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
    Generates HTML report with charts:
    1. Backend HPA
    2. Backend Pods
    3. Frontend HPA
    4. Frontend Pods
    5. Nodes
    6. DB Connection Pool (if data available)
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
    
    # Prepare DB Pool data (now collected at regular intervals)
    db_pool_labels = [d['time'] for d in db_pool_data]
    db_pool_total = [d['total'] for d in db_pool_data]
    db_pool_active = [d['active'] for d in db_pool_data]
    db_pool_idle = [d['idle'] for d in db_pool_data]
    db_pool_waiting = [d['waiting'] for d in db_pool_data]
    max_waiting = max(db_pool_waiting) if db_pool_waiting else 0
    max_active = max(db_pool_active) if db_pool_active else 0
    total_exhaustion_events = sum(1 for w in db_pool_waiting if w > 0)
    
    # Calculate pool utilization percentage for better visualization
    db_pool_utilization = []
    for i in range(len(db_pool_active)):
        total = db_pool_total[i] if db_pool_total[i] > 0 else 10
        util = (db_pool_active[i] / total) * 100
        db_pool_utilization.append(round(util, 1))
    
    avg_utilization = round(sum(db_pool_utilization) / len(db_pool_utilization), 1) if db_pool_utilization else 0
    max_utilization = max(db_pool_utilization) if db_pool_utilization else 0
    pool_size = db_pool_total[0] if db_pool_total else 10
    
    # DB Pool section HTML - show status based on whether exhaustion occurred
    has_exhaustion = max_waiting > 0 or total_exhaustion_events > 0
    
    # Determine status color based on utilization
    if has_exhaustion:
        status_bg = "#fee"
        status_border = "#e74c3c"
        status_icon = "⚠️"
        status_text = "Pool Exhaustion Detected!"
    elif max_utilization > 90:
        status_bg = "#fff3e0"
        status_border = "#f39c12"
        status_icon = "⚡"
        status_text = "High Pool Utilization"
    else:
        status_bg = "#efe"
        status_border = "#2ecc71"
        status_icon = "✅"
        status_text = "Pool Healthy"
    
    db_pool_section = f"""
    <!-- DB CONNECTION POOL SECTION -->
    <div class="row">
        <div class="col card" style="min-width: 100%;">
            <h2>🗄️ Database Connection Pool</h2>
            <div class="stat-box" style="background: {status_bg}; border: 2px solid {status_border}; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <span style="font-size: 1.4em;">{status_icon} {status_text}</span><br><br>
                <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px;">
                    <div style="text-align: center;">
                        <div style="font-size: 2em; font-weight: bold; color: #3498db;">{pool_size}</div>
                        <div style="font-size: 0.9em; color: #666;">Pool Size</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2em; font-weight: bold; color: {'#e74c3c' if max_utilization > 90 else '#f39c12' if max_utilization > 70 else '#2ecc71'};">{max_utilization}%</div>
                        <div style="font-size: 0.9em; color: #666;">Max Utilization</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2em; font-weight: bold; color: #9b59b6;">{avg_utilization}%</div>
                        <div style="font-size: 0.9em; color: #666;">Avg Utilization</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2em; font-weight: bold; color: {'#e74c3c' if max_waiting > 0 else '#2ecc71'};">{max_waiting}</div>
                        <div style="font-size: 0.9em; color: #666;">Max Queue Wait</div>
                    </div>
                </div>
            </div>
            <canvas id="dbPoolChart"></canvas>
        </div>
    </div>
    """
    
    db_pool_script = f"""
        // --- DB Connection Pool Chart ---
        const dbPoolLabels = {json.dumps(db_pool_labels)};
        const dbPoolTotal = {json.dumps(db_pool_total)};
        const dbPoolActive = {json.dumps(db_pool_active)};
        const dbPoolIdle = {json.dumps(db_pool_idle)};
        const dbPoolWaiting = {json.dumps(db_pool_waiting)};
        const dbPoolUtilization = {json.dumps(db_pool_utilization)};
        
        new Chart(document.getElementById('dbPoolChart'), {{
            type: 'bar',
            data: {{
                labels: dbPoolLabels,
                datasets: [
                    {{
                        label: 'Pool Utilization %',
                        data: dbPoolUtilization,
                        backgroundColor: dbPoolUtilization.map(v => 
                            v > 90 ? 'rgba(231, 76, 60, 0.8)' : 
                            v > 70 ? 'rgba(243, 156, 18, 0.8)' : 
                            'rgba(46, 204, 113, 0.8)'
                        ),
                        borderColor: dbPoolUtilization.map(v => 
                            v > 90 ? '#c0392b' : 
                            v > 70 ? '#d68910' : 
                            '#27ae60'
                        ),
                        borderWidth: 1,
                        yAxisID: 'y',
                        order: 2
                    }},
                    {{
                        label: 'Requests Waiting (Queue)',
                        data: dbPoolWaiting,
                        type: 'line',
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: '#e74c3c',
                        yAxisID: 'y1',
                        order: 1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        position: 'left',
                        title: {{ display: true, text: 'Pool Utilization (%)' }},
                        ticks: {{
                            callback: function(value) {{ return value + '%'; }}
                        }}
                    }},
                    y1: {{
                        beginAtZero: true,
                        position: 'right',
                        title: {{ display: true, text: 'Waiting Requests' }},
                        grid: {{ drawOnChartArea: false }}
                    }},
                    x: {{
                        title: {{ display: true, text: 'Time' }},
                        ticks: {{ maxTicksLimit: 20 }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'DB Connection Pool: Utilization & Queue (Red bars = >90% | Orange = >70% | Green = Healthy)'
                    }},
                    legend: {{
                        position: 'bottom'
                    }},
                    tooltip: {{
                        callbacks: {{
                            afterBody: function(context) {{
                                const idx = context[0].dataIndex;
                                return [
                                    '',
                                    'Pool Size: ' + dbPoolTotal[idx],
                                    'Active: ' + dbPoolActive[idx],
                                    'Idle: ' + dbPoolIdle[idx]
                                ];
                            }}
                        }}
                    }}
                }}
            }}
        }});
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>K8s Full Stack Metrics Report</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f4f4f4; }}
            .card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1, h2 {{ text-align: center; color: #333; }}
            .row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
            .col {{ flex: 1; min-width: 45%; }}
            canvas {{ max-height: 350px; }}
            .stat-box {{ text-align: center; margin-top: 15px; font-size: 1.1em; color: #666; }}
            .highlight {{ color: #e74c3c; font-weight: bold; font-size: 1.3em; }}
            .summary {{ background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .summary h2 {{ margin-top: 0; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
            .summary-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
            .summary-item .value {{ font-size: 2em; font-weight: bold; color: #333; }}
            .summary-item .label {{ font-size: 0.9em; color: #666; }}
        </style>
    </head>
    <body>
        <h1>🚀 Kubernetes Full Stack Scaling Report</h1>
        
        <!-- SUMMARY SECTION -->
        <div class="summary">
            <h2>📊 Test Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="value">{len(metrics_data) * POLL_INTERVAL}s</div>
                    <div class="label">Test Duration</div>
                </div>
                <div class="summary-item">
                    <div class="value">{max([d['backend']['ready_replicas'] for d in metrics_data]) if metrics_data else 0}</div>
                    <div class="label">Max Backend Pods</div>
                </div>
                <div class="summary-item">
                    <div class="value">{max([d['nodes']['ready'] for d in metrics_data]) if metrics_data else 0}</div>
                    <div class="label">Max Nodes</div>
                </div>
                <div class="summary-item">
                    <div class="value" style="color: {'#e74c3c' if max_waiting > 0 else '#2ecc71'};">{max_waiting}</div>
                    <div class="label">Max DB Queue Wait</div>
                </div>
            </div>
        </div>
        
        {db_pool_section}
        
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
                <h2>Cluster Nodes (Autoscaling)</h2>
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
                    ticks: {{ stepSize: 1 }}
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
            
            {db_pool_script}
        </script>
    </body>
    </html>
    """
    
    report_path = os.path.join(results_dir, "k8s_metrics.html")
    with open(report_path, "w") as f:
        f.write(html_content)
    
    print(f"📊 Kubernetes Metrics Report generated: {report_path}")
    print(f"   📈 DB Pool events captured: {len(db_pool_data)}")

def run_hpa_test():
    global monitoring_active, metrics_data, db_pool_data
    
    # Reset global data for fresh test
    metrics_data = []
    db_pool_data = []
    monitoring_active = True
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    locustfile_path = os.path.join(script_dir, "locustfile.py")
    results_dir = os.path.join(script_dir, OUTPUT_DIR)
    
    print(f"\n🚀 Starting HPA Test: {USER_CLASS}")
    print("🎯 Target: Trigger CPU > 50% to scale from 1 -> N replicas")
    print(f"⏱️  Duration: {TEST_DURATION} seconds")
    print(f"👥 Users: {USERS} | Spawn Rate: {SPAWN_RATE}/s")
    
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

    # Start K8s Metrics Monitoring (also polls DB pool metrics)
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
        print("   🗄️  DB pool metrics polled every", POLL_INTERVAL, "seconds...")

        subprocess.run(cmd, check=True)
        print("\n✅ Test Complete.")
        print(f"📊 Locust Report generated: {html_report}")
        
    except subprocess.CalledProcessError:
        print("\n⚠️ Test interrupted or failed.")
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user.")
    finally:
        monitoring_active = False
        print("\n   ⏳ Finalizing reports...")
        monitor_thread.join(timeout=5)
        generate_k8s_report(results_dir)
        print(f"\n📁 All reports saved to: {results_dir}")

if __name__ == "__main__":
    run_hpa_test()