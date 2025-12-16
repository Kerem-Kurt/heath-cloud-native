resource "null_resource" "build_backend" {
  triggers = {
    # Calculate hash of the backend source code to trigger rebuilds on changes
    # Only hashing specific directories to avoid scanning target/ or other ignored files
    src_sha1    = sha1(join("", [for f in fileset("${path.module}/../heatHBack/src", "**") : filesha1("${path.module}/../heatHBack/src/${f}")]))
    pom_sha1    = filesha1("${path.module}/../heatHBack/pom.xml")
    docker_sha1 = filesha1("${path.module}/../heatHBack/Dockerfile")
  }

  provisioner "local-exec" {
    # 1. Build the backend image
    command = <<EOT
      gcloud builds submit ${path.module}/../heatHBack \
        --tag ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.my_repo.repository_id}/heath-backend:latest \
        --project ${var.project_id} \
        --machine-type=E2_HIGHCPU_8
    EOT
  }

  depends_on = [
    google_artifact_registry_repository.my_repo,
    google_project_service.cloudbuild
  ]
}

resource "null_resource" "build_frontend" {
  triggers = {
    # Calculate hash of the frontend source code
    # Only hashing specific directories to avoid scanning node_modules/
    src_sha1    = sha1(join("", [for f in fileset("${path.module}/../heatHFront/React-Web/web/src", "**") : filesha1("${path.module}/../heatHFront/React-Web/web/src/${f}")]))
    public_sha1 = sha1(join("", [for f in fileset("${path.module}/../heatHFront/React-Web/web/public", "**") : filesha1("${path.module}/../heatHFront/React-Web/web/public/${f}")]))
    pkg_sha1    = filesha1("${path.module}/../heatHFront/React-Web/web/package.json")
    docker_sha1 = filesha1("${path.module}/../heatHFront/React-Web/web/Dockerfile")
    nginx_sha1  = filesha1("${path.module}/../heatHFront/React-Web/web/nginx.conf")
  }

  provisioner "local-exec" {
    command = <<EOT
      gcloud builds submit ${path.module}/../heatHFront/React-Web/web \
        --tag ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.my_repo.repository_id}/heath-frontend:latest \
        --project ${var.project_id} \
        --machine-type=E2_HIGHCPU_8
    EOT
  }

  depends_on = [
    google_artifact_registry_repository.my_repo,
    google_project_service.cloudbuild
  ]
}
