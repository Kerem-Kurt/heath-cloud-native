resource "google_artifact_registry_repository" "my_repo" {
  location      = var.region
  repository_id = "heath-repo"
  description   = "Docker repository for Heath application"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}

# Grant GKE Service Account permission to pull images from this repository
resource "google_artifact_registry_repository_iam_member" "gke_sa_pull" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.my_repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.gke_sa.email}"
}
