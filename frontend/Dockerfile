# ====================================================================
# AI-RCI Frontend — React + Vite Multi-Stage Build
# ====================================================================
# Stage 1: Build the React app
# Stage 2: Serve with Nginx (production-grade)
# ====================================================================

# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first (Docker cache optimization)
COPY package.json ./
RUN npm install --legacy-peer-deps

# Copy source code and build
COPY . .

# Set the backend API URL for production builds
# This should point to the backend Kubernetes service or load balancer
ARG VITE_API_URL=http://airci-backend-svc:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---- Stage 2: Serve with Nginx ----
FROM nginx:1.25-alpine

# Copy custom Nginx config template for dynamic environment variables
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy built React assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
