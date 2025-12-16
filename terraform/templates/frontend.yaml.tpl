apiVersion: apps/v1
kind: Deployment
metadata:
  name: heath-frontend
spec:
  replicas: ${hpa_min_replicas}
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: ${region}-docker.pkg.dev/${project_id}/${repo_name}/heath-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: REACT_APP_API_URL
          value: "http://heath-backend"
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
  name: heath-frontend
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
  loadBalancerIP: ${frontend_ip}
%{ if hpa_enabled }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: heath-frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: heath-frontend
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
