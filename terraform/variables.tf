variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP Zone"
  type        = string
  default     = "us-central1-a"
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
