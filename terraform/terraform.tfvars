project_id       = "heath-cloud-native-5"
region           = "us-central1"
zone             = "us-central1-a"
sendgrid_api_key = "SENDGRID_API_KEY"
sender_email     = "SENDGRID_SENDER_EMAIL"

# ================== Database ==================
db_machine_type = "e2-medium" # 2 vCPUs, 4 GB RAM
db_disk_size    = 20 # GB
db_image        = "ubuntu-os-cloud/ubuntu-2204-lts"

# ================== GKE Cluster ==================
gke_node_machine_type = "e2-standard-2"
gke_node_count        = 1

# If autoscaling is enabled, the min and max node counts are used.
gke_autoscaling_enabled = false
gke_min_node_count      = 1
gke_max_node_count      = 1


# ================== Backend ==================
# The resources guaranteed to each backend pod.
backend_cpu_request      = "250m" # 0.25 vCPU
backend_memory_request   = "512Mi" # 0.5 GB

# The maximum resources a backend pod is allowed to use.
# If it tries to use more, it may be restarted.
backend_cpu_limit        = "500m" # 0.5 vCPU
backend_memory_limit     = "1Gi" # 1 GB

# If HPA is enabled, the min and max replicas are used.
backend_hpa_enabled      = true
backend_hpa_min_replicas = 1
backend_hpa_max_replicas = 3
backend_hpa_cpu_target   = 70 # percentage

# ================== Frontend ==================
# The resources guaranteed to each frontend pod.
frontend_cpu_request      = "250m" # 0.25 vCPU
frontend_memory_request   = "512Mi" # 0.5 GB

# The maximum resources a frontend pod is allowed to use.
frontend_cpu_limit        = "500m" # 0.5 vCPU
frontend_memory_limit     = "1Gi" # 1 GB

# If HPA is enabled, the min and max replicas are used.
frontend_hpa_enabled      = false
frontend_hpa_min_replicas = 1
frontend_hpa_max_replicas = 5
frontend_hpa_cpu_target   = 70 # percentage

# ================== Cloud Function ==================
function_max_instances = 10
function_memory        = "512M" # 0.512 GB
function_timeout       = 60
