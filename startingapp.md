# 🚀 AI-RCI Platform: Getting Started & Deployment Guide

This guide contains the exact step-by-step instructions, environment variables, database definitions, and AWS prerequisites required to deploy the AI-RCI microservices platform in a production Kubernetes environment.

---

## 🏗️ 1. AWS Pre-Requisites

Before deploying the code, you must provision the following cloud infrastructure in AWS:

1. **Amazon EKS (Elastic Kubernetes Service)**
   - Create an EKS Cluster (e.g., Kubernetes version 1.28+).
   - Configure Node Groups (e.g., `t3.medium` instances).
2. **Amazon Bedrock**
   - Go to the AWS Bedrock console in `us-east-1`.
   - Navigate to **Model Access** and request access to **Anthropic Claude 3.5 Sonnet**.
3. **Amazon ECR (Elastic Container Registry)**
   - Create two private repositories: `airci-frontend` and `airci-backend`.
4. **AWS IAM (Identity and Access Management)**
   - Create an IAM Role for Service Accounts (IRSA) for the Backend pod that grants it `bedrock:InvokeModel` permissions.

---

## 🗄️ 2. Persistent Memory Configuration (Hindsight)

The application uses **Vectorize Hindsight** to store the SRE Prompt Cache and historical analysis logs. 
When the backend boots up, it automatically initializes the Hindsight memory bank on the cloud.

### Where to define the API keys:
You must define the credentials securely in Kubernetes using a **Secret**.

**File:** `infrastructure/k8s/db-secret.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: airci-db-secret
  namespace: airci
type: Opaque
data:
  # Values MUST be Base64 encoded. (e.g., echo -n "hsk_..." | base64)
  HINDSIGHT_API_KEY: <BASE64_ENCODED_HINDSIGHT_API_KEY>
```

---

## ⚙️ 3. Environment Variables for Deployments

To ensure maximum security and flexibility, the application images do not contain any hardcoded targets. They rely entirely on environment variables passed during deployment.

### A. Backend Deployment Variables
The Backend (FastAPI) pod requires the following environment variables:

| Variable Name | Pulled From | Description |
|---|---|---|
| `HINDSIGHT_API_KEY` | `db-secret` | The Vectorize Hindsight API Key. |
| `AWS_REGION` | `configmap` | Region where Bedrock is active (e.g., `us-east-1`). |
| `DEFAULT_LLM_PROVIDER` | `configmap` | Set to `bedrock`. |

### B. Frontend Deployment Variables
The Frontend (React + Nginx) pod requires the following environment variable to know where to route API traffic:

| Variable Name | Pulled From | Description |
|---|---|---|
| `BACKEND_API_URL` | `configmap` | URL to the backend service. Inside Kubernetes, this should be the internal Service DNS: `http://airci-backend-svc:8000`. |

*(Note: Nginx uses `envsubst` to dynamically inject this `BACKEND_API_URL` variable into its routing configuration at startup.)*

---

## 🚀 4. Step-by-Step Application Startup

Once your AWS pre-requisites are ready, follow these exact steps to start the application:

### Step 1: Build & Push Docker Images
```bash
# Build Backend
docker build -f backend/Dockerfile -t <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/airci-backend:latest ./backend
docker push <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/airci-backend:latest

# Build Frontend
docker build -f frontend/Dockerfile -t <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/airci-frontend:latest ./frontend
docker push <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/airci-frontend:latest
```

### Step 2: Inject Configurations to Kubernetes
Update your `db-secret.yaml` and `configmap.yaml` with your actual values, then apply them:
```bash
kubectl create namespace airci
kubectl apply -f infrastructure/k8s/db-secret.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
```

### Step 3: Deploy the Backend and Frontend
The deployment files are already configured to pull the environment variables mapped above.
```bash
kubectl apply -f infrastructure/k8s/backend-deployment.yaml
kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
```

### Step 4: Verify and Access
```bash
# Ensure all pods are running (Backend x2, Frontend x2)
kubectl get pods -n airci

# Get the public LoadBalancer URL for the React dashboard
kubectl get svc airci-frontend-svc -n airci
```
Copy the `EXTERNAL-IP` from the output and open it in your browser. The application is now live, connected to Hindsight, and fully utilizing AWS Bedrock!

---

## 💻 5. Running Locally (Alternative)
If you just want to test the full microservices stack on your local laptop without deploying to Kubernetes, simply use the pre-configured Docker Compose file:

```bash
docker-compose up --build
```
This single command will:
1. Build and start the Backend.
2. Build and start the Frontend, automatically passing `BACKEND_API_URL=http://backend:8000`.
3. Dashboard is instantly accessible at **`http://localhost:3000`**.
