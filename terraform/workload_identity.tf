resource "google_service_account" "backend_wi_sa" {
  account_id   = "heath-backend-sa"
  display_name = "K8s Backend Service Account"
}

resource "google_storage_bucket_iam_member" "backend_wi_storage_admin" {
  bucket = google_storage_bucket.media_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend_wi_sa.email}"
}

resource "google_service_account_iam_member" "wi_user" {
  service_account_id = google_service_account.backend_wi_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/heath-backend-sa]"
}
