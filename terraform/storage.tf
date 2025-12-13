resource "google_storage_bucket" "media_bucket" {
  name          = "${var.project_id}-media"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  # Grant read access to everyone (public) or specific users
  # For a profile photo, usually we want it public or signed URLs. 
  # Here we'll make it public for simplicity if that's the intention, 
  # or keep it private and use signed URLs. 
  # The code returns "https://storage.googleapis.com/..." which implies public access 
  # OR the user needs to be authenticated with Google to view it.
  # For a web app, public read is common for profile photos.
}

# Make the bucket public (Optional - depending on requirements)
resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.media_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

output "media_bucket_name" {
  value = google_storage_bucket.media_bucket.name
}
