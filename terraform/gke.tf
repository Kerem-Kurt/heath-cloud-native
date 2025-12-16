resource "google_service_account" "gke_sa" {
  account_id   = "heath-gke-node-sa"
  display_name = "GKE Node Service Account"
}

# Grant the recommended role for GKE node service accounts
resource "google_project_iam_member" "gke_sa_default_role" {
  project = var.project_id
  role    = "roles/container.defaultNodeServiceAccount"
  member  = "serviceAccount:${google_service_account.gke_sa.email}"
}


resource "google_container_cluster" "primary" {
  name       = "heath-cluster"
  location   = var.zone
  depends_on = [google_project_service.container]

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = var.gke_min_node_count

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.subnet.id

  # VPC-native cluster configuration
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Workload Identity allows Kubernetes service accounts to act as Google IAM Service Accounts
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "heath-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = 1

  autoscaling {
    min_node_count = var.gke_min_node_count
    max_node_count = var.gke_max_node_count
  }

  node_config {
    machine_type = var.gke_node_machine_type

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # We use preemptible nodes to save costs (Optional - good for dev/testing)
    # preemptible  = true

    labels = {
      role = "general"
    }

    tags = ["gke-node", "heath-gke"]
  }
}

# --- Workload Identity Setup for Backend ---

# 1. Create Google Service Account for Backend
resource "google_service_account" "backend_sa" {
  account_id   = "heath-backend-sa"
  display_name = "Heath Backend Service Account"
}

# 2. Allow Kubernetes SA (default/heath-backend-sa) to impersonate Google SA
resource "google_service_account_iam_member" "backend_sa_impersonation" {
  service_account_id = google_service_account.backend_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/heath-backend-sa]"
  depends_on         = [google_container_cluster.primary]
}
