project_id       = "heath-cloud-native-kerem-1"
region           = "us-central1"
zone             = "us-central1-a"
sendgrid_api_key = "SENDGRID_API_KEY"
sender_email     = "SENDGRID_SENDER_EMAIL"

# Database
db_machine_type = "e2-medium" # 2 vCPUs, 4 GB RAM
db_disk_size    = 20 # GB
db_image        = "ubuntu-os-cloud/ubuntu-2204-lts"

# GKE Cluster
gke_node_machine_type = "e2-standard-2"
gke_node_count        = 1
gke_min_node_count    = 1
gke_max_node_count    = 3
gke_autoscaling_enabled = true

# Backend
backend_cpu_request      = "250m" # 0.25 vCPU
backend_memory_request   = "512Mi" # 0.5 GB
backend_cpu_limit        = "500m" # 0.5 vCPU
backend_memory_limit     = "1Gi" # 1 GB
backend_hpa_enabled      = true
backend_hpa_min_replicas = 1
backend_hpa_max_replicas = 10
backend_hpa_cpu_target   = 70 # percentage

# Frontend
frontend_cpu_request      = "250m" # 0.25 vCPU
frontend_memory_request   = "512Mi" # 0.5 GB
frontend_cpu_limit        = "500m" # 0.5 vCPU
frontend_memory_limit     = "1Gi" # 1 GB
frontend_hpa_enabled      = false
frontend_hpa_min_replicas = 1
frontend_hpa_max_replicas = 3
frontend_hpa_cpu_target   = 70 # percentage

# Cloud Function
function_max_instances = 10
function_memory        = "512M" # 0.512 GB
function_timeout       = 60
