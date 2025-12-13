resource "google_artifact_registry_repository" "my_repo" {
  location      = var.region
  repository_id = "heath-repo"
  description   = "Docker repository for Heath application"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}
