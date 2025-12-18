resource "google_compute_instance" "postgres_vm" {
  name         = "heath-postgres-vm"
  machine_type = var.db_machine_type
  zone         = var.zone

  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = var.db_image
      size  = var.db_disk_size
    }
  }

  network_interface {
    network    = google_compute_network.vpc.id
    subnetwork = google_compute_subnetwork.subnet.id
    # We do NOT assign an external IP (access_config block) for security, 
    # but for debugging ease we can add one. 
    # If we want strictly internal, we remove the access_config block.
    # For this setup, we'll keep it internal-only or add NAT. 
    # To keep it simple and accessible for installation/updates (apt-get), 
    # we'll add an ephemeral public IP.
    access_config {
      # Ephemeral public IP
    }
  }

  tags = ["ssh-enabled", "postgres-server"]

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e

    # Install PostgreSQL
    apt-get update
    apt-get install -y postgresql postgresql-contrib

    # Configure PostgreSQL to listen on all interfaces
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf

    # Allow connections from the VPC subnet (Nodes) and Pod CIDR
    echo "host all all ${var.subnet_cidr} md5" >> /etc/postgresql/*/main/pg_hba.conf
    echo "host all all ${var.pod_cidr} md5" >> /etc/postgresql/*/main/pg_hba.conf

    # Restart PostgreSQL to apply changes
    systemctl restart postgresql

    # Create User and Database
    # We use sudo -u postgres to run psql commands
    sudo -u postgres psql -c "CREATE USER ${var.db_user} WITH PASSWORD '${var.db_password}';" || true
    sudo -u postgres psql -c "CREATE DATABASE ${var.db_name} OWNER ${var.db_user};" || true
    
    # Grant privileges
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${var.db_name} TO ${var.db_user};"
  EOF
}
