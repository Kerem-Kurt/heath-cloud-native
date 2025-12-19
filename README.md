# Heath Cloud Native

<img width="851" height="254" alt="Ekran Resmi 2025-12-19 15 48 15" src="https://github.com/user-attachments/assets/5c53e102-bb7f-4f8e-b90d-5df49bd88c7d" />

This project is a cloud-native application deployed on Google Cloud Platform (GCP) using Terraform.

## Project Structure

*   **`heatHBack`**: Spring Boot Backend Application.
*   **`heatHFront`**: React Frontend Application.
*   **`terraform`**: Infrastructure as Code (IaC) configuration to provision GCP resources.
*   **`k8s`**: Kubernetes manifests.
*   **`functions`**: Google Cloud Functions (Java).
*   **`locust`**: Load testing scripts using Locust.

## Prerequisites

Ensure you have the following tools installed on your local machine:

*   [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install)
*   [Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.5.0+)
*   [kubectl](https://kubernetes.io/docs/tasks/tools/) (optional, for cluster management)

## Setup & Deployment Instructions

### 1. Google Cloud Authentication

First, authenticate with Google Cloud to allow Terraform to create resources.

1.  Login to your Google Cloud account:
    ```bash
    gcloud auth login
    ```

2.  Set your project ID:
    ```bash
    gcloud config set project <your-gcp-project-id>
    ```

3.  Configure Application Default Credentials (ADC) for Terraform:
    ```bash
    gcloud auth application-default login
    gcloud auth application-default set-quota-project <your-gcp-project-id>
    ```

### 2. Configure Terraform

1.  Navigate to the `terraform` directory:
    ```bash
    cd terraform
    ```

2.  Open `terraform.tfvars` and update the values for your environment.
    *   **Important**: You **must** update the `project_id` to match your GCP Project ID.
    *   Update `sendgrid_api_key` and `sender_email` if you want email functionality to work.

    Example `terraform.tfvars`:
    ```hcl
    project_id = "your-gcp-project-id"
    ```

### 3. Deploy Infrastructure

1.  Initialize Terraform:
    ```bash
    terraform init
    ```

2.  Plan the deployment to see what will be created:
    ```bash
    terraform plan
    ```

3.  Apply the configuration to create the infrastructure:
    ```bash
    terraform apply
    ```
    *   Type `yes` when prompted to confirm.
    *   **Note**: This process automatically builds the Docker images for the Frontend and Backend using Google Cloud Build and pushes them to the Artifact Registry. The initial deployment can take 15-20 minutes.

### 4. Access the Application

Once `terraform apply` completes successfully, you will see several outputs in your terminal:

*   **`frontend_external_ip`**: The public IP address to access the web application. Open this in your browser.
*   **`vm_public_ip`**: The public IP of the PostgreSQL Database VM.
*   **`get_credentials_command`**: A command to configure `kubectl` to connect to your new GKE cluster.

To view these outputs again later, run:
```bash
terraform output
```

## Testing & Monitoring

*   **Kubernetes**: Use the `get_credentials_command` output to configure `kubectl`, then use standard commands like `kubectl get pods` to check the status of your deployments.

*   **Load Testing with Locust**:
    The `locust` directory contains scripts for load testing the application's auto-scaling capabilities.

    1.  **Install Locust**:
        ```bash
        pip install locust
        ```

    2.  **Configure Test Parameters**:
        *   **Load Config**: You can modify `USERS` and `SPAWN_RATE` directly in `locust/run_hpa.py` to simulate different traffic patterns.
        *   **Infrastructure Config**: You can tune scaling behavior (like `gke_max_node_count`, `backend_hpa_max_replicas`) in `terraform/terraform.tfvars` and apply changes with `terraform apply`.

    3.  **Run the Test**:
        ```bash
        python locust/run_hpa.py
        ```
        This will start the load test and generate HTML reports in the `locust/results_hpa` directory, visualizing HPA scaling, Pod CPU usage, and Database Connection Pool status.

## Cleanup

To destroy all resources and avoid incurring further costs:

```bash
cd terraform
terraform destroy
```
