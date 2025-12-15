resource "google_pubsub_topic" "email_topic" {
  name = "send-email"
}

# Bucket to store the Cloud Function source code
resource "google_storage_bucket" "function_bucket" {
  name     = "${var.project_id}-function-source"
  location = var.region
  uniform_bucket_level_access = true
}

# Zip up the Cloud Function code (we will create this directory next)
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/email-sender"
  output_path = "${path.module}/function-source.zip"
}

# Upload the zip to the bucket
resource "google_storage_bucket_object" "function_archive" {
  name   = "email-sender-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_zip.output_path
}

# Cloud Function (Gen 2)
resource "google_cloudfunctions2_function" "email_function" {
  name        = "email-sender-function"
  location    = var.region
  description = "Sends emails via SendGrid triggered by Pub/Sub"

  build_config {
    runtime     = "java17"
    entry_point = "functions.EmailSender" # Adjust based on your Java package
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_archive.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      SENDGRID_API_KEY = var.sendgrid_api_key
      SENDER_EMAIL     = var.sender_email
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.email_topic.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.eventarc,
    google_project_service.pubsub
  ]
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.email_topic.name
}
