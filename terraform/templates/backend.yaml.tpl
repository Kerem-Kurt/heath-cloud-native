apiVersion: v1
kind: ServiceAccount
metadata:
  name: heath-backend-sa
  annotations:
    iam.gke.io/gcp-service-account: ${backend_sa_email}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: heath-backend
spec:
  replicas: ${hpa_min_replicas}
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      serviceAccountName: heath-backend-sa
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: backend
      containers:
      - name: backend
        image: ${region}-docker.pkg.dev/${project_id}/${repo_name}/heath-backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: DB_URL
          value: "jdbc:postgresql://${db_ip}:5432/${db_name}"
        - name: DB_USERNAME
          value: "${db_user}"
        - name: DB_PASSWORD
          value: "${db_password}"
        - name: GCP_PROJECT_ID
          value: "${project_id}"
        - name: GCP_BUCKET
          value: "${media_bucket}"
        - name: APP_BASE_URL
          value: "http://${frontend_ip}"
        - name: MAIL_HOST
          value: "smtp.sendgrid.net"
        - name: MAIL_PORT
          value: "587"
        - name: MAIL_USERNAME
          value: "apikey"
        - name: MAIL_PASSWORD
          value: "placeholder_password"
        - name: SENDGRID_API_KEY
          value: "placeholder_key"
        - name: FATSECRET_CLIENT_ID
          value: "placeholder_id"
        - name: FATSECRET_CLIENT_SECRET
          value: "placeholder_secret"
        - name: SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE
          value: "${db_pool_size}"
        resources:
          requests:
            cpu: "${cpu_request}"
            memory: "${memory_request}"
          limits:
            cpu: "${cpu_limit}"
            memory: "${memory_limit}"
---
apiVersion: v1
kind: Service
metadata:
  name: heath-backend
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
%{ if hpa_enabled }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: heath-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: heath-backend
  minReplicas: ${hpa_min_replicas}
  maxReplicas: ${hpa_max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: ${hpa_cpu_target}
%{ endif }
