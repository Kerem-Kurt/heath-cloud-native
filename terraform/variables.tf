variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  #default     = "us-central1"
}

variable "zone" {
  description = "The GCP Zone"
  type        = string
  #default     = "us-central1-a"
}

variable "vpc_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "heath-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "heath-subnet"
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet (Nodes & VM)"
  type        = string
  default     = "10.0.0.0/24"
}

variable "pod_cidr" {
  description = "CIDR block for GKE Pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "svc_cidr" {
  description = "CIDR block for GKE Services"
  type        = string
  default     = "10.2.0.0/20"
}

variable "db_password" {
  description = "Password for the database user"
  type        = string
  sensitive   = true
  default     = "securepassword123" # In production, pass this via tfvars or env var
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "heathuser"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "heathdb"
}

variable "sendgrid_api_key" {
  description = "The SendGrid API Key for sending emails"
  type        = string
  sensitive   = true
}

variable "sender_email" {
  description = "The email address to send from"
  type        = string
}

# --- Database Config ---
variable "db_machine_type" {
  description = "Machine type for the Database VM"
  type        = string
  default     = "e2-medium"
}

variable "db_disk_size" {
  description = "Boot disk size for the Database VM in GB"
  type        = number
  default     = 20
}

variable "db_image" {
  description = "Image for the Database VM"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

# --- GKE Config ---
variable "gke_node_machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "e2-standard-2"
}

variable "gke_node_count" {
  description = "Number of nodes in the node pool (used if autoscaling is disabled or as initial count)"
  type        = number
  default     = 1
}

variable "gke_min_node_count" {
  description = "Minimum number of nodes in the node pool"
  type        = number
  default     = 1
}

variable "gke_max_node_count" {
  description = "Maximum number of nodes in the node pool"
  type        = number
  default     = 3
}

variable "gke_autoscaling_enabled" {
  description = "Enable autoscaling for GKE node pool"
  type        = bool
  default     = true
}

# --- Backend Config ---
variable "backend_cpu_request" {
  description = "CPU request for backend container"
  type        = string
  default     = "250m"
}

variable "backend_memory_request" {
  description = "Memory request for backend container"
  type        = string
  default     = "512Mi"
}

variable "backend_cpu_limit" {
  description = "CPU limit for backend container"
  type        = string
  default     = "500m"
}

variable "backend_memory_limit" {
  description = "Memory limit for backend container"
  type        = string
  default     = "1Gi"
}

variable "backend_hpa_enabled" {
  description = "Enable HPA for backend"
  type        = bool
  default     = true
}

variable "backend_hpa_min_replicas" {
  description = "Min replicas for backend HPA"
  type        = number
  default     = 1
}

variable "backend_hpa_max_replicas" {
  description = "Max replicas for backend HPA"
  type        = number
  default     = 5
}

variable "backend_hpa_cpu_target" {
  description = "Target CPU utilization percentage for backend HPA"
  type        = number
  default     = 70
}

# --- Frontend Config ---
variable "frontend_cpu_request" {
  description = "CPU request for frontend container"
  type        = string
  default     = "250m"
}

variable "frontend_memory_request" {
  description = "Memory request for frontend container"
  type        = string
  default     = "512Mi"
}

variable "frontend_cpu_limit" {
  description = "CPU limit for frontend container"
  type        = string
  default     = "500m"
}

variable "frontend_memory_limit" {
  description = "Memory limit for frontend container"
  type        = string
  default     = "1Gi"
}

variable "frontend_hpa_enabled" {
  description = "Enable HPA for frontend"
  type        = bool
  default     = true
}

variable "frontend_hpa_min_replicas" {
  description = "Min replicas for frontend HPA"
  type        = number
  default     = 1
}

variable "frontend_hpa_max_replicas" {
  description = "Max replicas for frontend HPA"
  type        = number
  default     = 5
}

variable "frontend_hpa_cpu_target" {
  description = "Target CPU utilization percentage for frontend HPA"
  type        = number
  default     = 70
}

# --- Cloud Function Config ---
variable "function_max_instances" {
  description = "Max instances for the Cloud Function"
  type        = number
  default     = 10
}

variable "function_memory" {
  description = "Available memory for the Cloud Function"
  type        = string
  default     = "256M"
}

variable "function_timeout" {
  description = "Timeout in seconds for the Cloud Function"
  type        = number
  default     = 60
}
