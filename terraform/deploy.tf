resource "local_file" "backend_manifest" {
  content = templatefile("${path.module}/templates/backend.yaml.tpl", {
    backend_sa_email = google_service_account.backend_sa.email
    region           = var.region
    project_id       = var.project_id
    repo_name        = google_artifact_registry_repository.my_repo.repository_id
    db_ip            = google_compute_instance.postgres_vm.network_interface[0].network_ip
    db_name          = var.db_name
    db_user          = var.db_user
    db_password      = var.db_password
    media_bucket     = google_storage_bucket.media_bucket.name
    frontend_ip      = google_compute_address.frontend_ip.address
    cpu_request      = var.backend_cpu_request
    memory_request   = var.backend_memory_request
    cpu_limit        = var.backend_cpu_limit
    memory_limit     = var.backend_memory_limit
    hpa_enabled      = var.backend_hpa_enabled
    hpa_min_replicas = var.backend_hpa_min_replicas
    hpa_max_replicas = var.backend_hpa_max_replicas
    hpa_cpu_target   = var.backend_hpa_cpu_target
  })
  filename = "${path.module}/../k8s/generated/backend.yaml"
}

resource "local_file" "frontend_manifest" {
  content = templatefile("${path.module}/templates/frontend.yaml.tpl", {
    region           = var.region
    project_id       = var.project_id
    repo_name        = google_artifact_registry_repository.my_repo.repository_id
    frontend_ip      = google_compute_address.frontend_ip.address
    cpu_request      = var.frontend_cpu_request
    memory_request   = var.frontend_memory_request
    cpu_limit        = var.frontend_cpu_limit
    memory_limit     = var.frontend_memory_limit
    hpa_enabled      = var.frontend_hpa_enabled
    hpa_min_replicas = var.frontend_hpa_min_replicas
    hpa_max_replicas = var.frontend_hpa_max_replicas
    hpa_cpu_target   = var.frontend_hpa_cpu_target
  })
  filename = "${path.module}/../k8s/generated/frontend.yaml"
}

resource "null_resource" "deploy_manifests" {
  triggers = {
    # Redeploy if manifests change or builds update
    backend_manifest_sha1  = local_file.backend_manifest.content_sha512
    frontend_manifest_sha1 = local_file.frontend_manifest.content_sha512
    backend_build_id       = null_resource.build_backend.id
    frontend_build_id      = null_resource.build_frontend.id
  }

  provisioner "local-exec" {
    command = <<EOT
      gcloud container clusters get-credentials ${google_container_cluster.primary.name} --zone ${var.zone} --project ${var.project_id}
      kubectl apply -f ${path.module}/../k8s/generated/backend.yaml
      kubectl apply -f ${path.module}/../k8s/generated/frontend.yaml
      
      # Force restart to pick up new images if they were just rebuilt but manifests didn't change
      kubectl rollout restart deployment/heath-backend
      kubectl rollout restart deployment/heath-frontend
    EOT
  }

  depends_on = [
    google_container_cluster.primary,
    google_container_node_pool.primary_nodes,
    null_resource.build_backend,
    null_resource.build_frontend
  ]
}

