# Local Development Setup & Coding Standards

## 1. Prerequisites
- Docker Desktop
- Minikube
- Python 3.11+
- Node 20+

## 2. Bootstrapping Local Cluster
```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
```

## 3. Coding Standards
- **Python**: Use `black` for formatting, `mypy` for static typing, and `isort` for imports. All code MUST be async using FastAPI and AsyncIO.
- **Node/React**: Use strict TypeScript, `eslint`, and `prettier`. 
- **SOLID**: Follow single-responsibility in every class/function. Do not build God objects.
- **Logging**: Do NOT use `print()`. Use the shared `structlog` framework from `pkg.core.logging`.
- **Errors**: Raise `Hindsight Incident AgentException` from `pkg.core.errors` instead of standard HTTPExceptions to maintain the enterprise JSON response structure.

## 4. API Response Standards
All APIs must return structured JSON or standard standard HTTP status codes:
- 200 OK / 201 Created
- 400 Bad Request (Invalid input)
- 401 Unauthorized (Missing JWT)
- 403 Forbidden (RBAC violation)
- 500 Internal Server Error (Wrapped in ErrorResponse format)

See `pkg.core.errors.ErrorResponse` for the schema.
