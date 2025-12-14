# VPC Network
resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  depends_on              = [google_project_service.compute]
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = var.subnet_name
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = var.subnet_cidr

  # Secondary ranges for GKE (VPC-native)
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pod_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.svc_cidr
  }
}

# Firewall Rule: Allow internal communication (GKE Pods/Nodes <-> VM)
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  # Allow traffic from Subnet (Nodes/VM) AND Pods range
  source_ranges = [var.subnet_cidr, var.pod_cidr]
}

# Firewall Rule: Allow SSH (Optional, for debugging VM)
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.vpc_name}-allow-ssh"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"] # WARNING: Limit this to your IP in production
  target_tags   = ["ssh-enabled"]
}

# Static External IP for Frontend LoadBalancer
resource "google_compute_address" "frontend_ip" {
  name       = "heath-frontend-ip"
  region     = var.region
  depends_on = [google_project_service.compute]
}
