output "vpc_name" {
  description = "The name of the VPC"
  value       = google_compute_network.vpc.name
}

output "vm_internal_ip" {
  description = "Internal IP of the PostgreSQL VM"
  value       = google_compute_instance.postgres_vm.network_interface[0].network_ip
}

output "vm_public_ip" {
  description = "Public IP of the PostgreSQL VM (Ephemeral)"
  value       = google_compute_instance.postgres_vm.network_interface[0].access_config[0].nat_ip
}

output "frontend_external_ip" {
  description = "External IP address of the Frontend LoadBalancer"
  value       = google_compute_address.frontend_ip.address
}

output "cluster_name" {
  description = "GKE Cluster Name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE Cluster Endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "get_credentials_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --zone ${var.zone} --project ${var.project_id}"
}
