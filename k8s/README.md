# TriageIQ Kubernetes Manifests

Example manifests for running TriageIQ on a Kubernetes cluster. These are **optional** — local development and Docker Compose are unchanged.

## Contents

| File | Description |
|------|-------------|
| `configmap.yaml` | Non-sensitive env vars (MongoDB URI, CORS, JWT settings) |
| `secret.example.yaml` | Secret template for `JWT_SECRET` (no real values) |
| `mongodb-deployment.yaml` | MongoDB 7.0 Deployment + PVC |
| `mongodb-service.yaml` | MongoDB ClusterIP Service (`triageiq-mongodb:27017`) |
| `backend-deployment.yaml` | FastAPI backend Deployment |
| `backend-service.yaml` | Backend ClusterIP Service (`triageiq-backend:8000`) |
| `frontend-deployment.yaml` | React/Vite frontend Deployment |
| `frontend-service.yaml` | Frontend ClusterIP Service (`triageiq-frontend:5173`) |

The backend `MONGODB_URI` in the ConfigMap points at the MongoDB Service DNS name:

```text
mongodb://triageiq-mongodb:27017/triageiq
```

## Prerequisites

- Kubernetes cluster (minikube, kind, Docker Desktop Kubernetes, etc.)
- `kubectl` configured
- Docker images built locally:

```bash
docker build -t triageiq-backend:latest ./backend
docker build -t triageiq-frontend:latest ./frontend
```

For **minikube** or **kind**, load images into the cluster:

```bash
minikube image load triageiq-backend:latest
minikube image load triageiq-frontend:latest
```

## Apply order

1. **Create the JWT secret** (required — not stored in ConfigMap):

```bash
kubectl create secret generic triageiq-secrets \
  --from-literal=jwt-secret='your-strong-random-secret'
```

2. **Apply ConfigMap and workloads**:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mongodb-deployment.yaml
kubectl apply -f k8s/mongodb-service.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

Or apply everything except the example secret in one step:

```bash
kubectl apply -f k8s/configmap.yaml \
  -f k8s/mongodb-deployment.yaml \
  -f k8s/mongodb-service.yaml \
  -f k8s/backend-deployment.yaml \
  -f k8s/backend-service.yaml \
  -f k8s/frontend-deployment.yaml \
  -f k8s/frontend-service.yaml
```

3. **Verify**:

```bash
kubectl get pods,svc,pvc
kubectl logs deploy/triageiq-backend
```

## Accessing the app

Services default to `ClusterIP`. For local clusters, port-forward:

```bash
kubectl port-forward svc/triageiq-backend 8000:8000
kubectl port-forward svc/triageiq-frontend 5173:5173
```

Then open http://localhost:5173 (API at http://localhost:8000).

Update `VITE_API_BASE_URL` and `CORS_ORIGINS` in `configmap.yaml` if you expose services via Ingress or NodePort instead of port-forwarding.

## Teardown

```bash
kubectl delete -f k8s/ --ignore-not-found
kubectl delete secret triageiq-secrets --ignore-not-found
```

## Notes

- No real secrets are committed; only `secret.example.yaml` shows the expected shape.
- Docker Compose (`docker-compose.yml`) remains the recommended local dev path.
- For production, use a managed MongoDB service, Ingress with TLS, and stronger resource limits.
