# Deployment Guide

This document provides instructions for deploying the Eternity2 application in various environments, with a focus on production deployment behind a reverse proxy.

## Table of Contents
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Deployment Behind Reverse Proxy](#deployment-behind-reverse-proxy)
- [Environment Variables](#environment-variables)
- [Port Configuration](#port-configuration)

## Local Development

### Quick Start with Docker Compose

1. Clone the repository
2. Run the application:
   ```bash
   docker compose up -d
   ```
3. Access the application at `http://localhost:80`
4. The Envoy proxy (gRPC-Web gateway) is available at `http://localhost:50052`

### Building from Source

If you want to build the images locally instead of using pre-built images:

1. Edit `docker-compose/docker-compose.yaml` and uncomment the `build` sections
2. Build all images:
   ```bash
   make docker-build
   ```
3. Start the services:
   ```bash
   make up
   # Or: docker compose -f docker-compose/docker-compose.yaml up -d
   ```

## Production Deployment

### Building Production Images

```bash
# Set your Docker registry
export DOCKER_REGISTRY=your-registry.com/eternity2
export DOCKER_TAG=v1.0.0

# Build all images
make docker-build

# Push to registry
make docker-push-all
```

### Deploying to Production

1. Update `docker-compose/docker-compose.yaml` (or `docker-compose/docker-compose.prod.yaml`) with your registry URLs
2. Set environment variables for your production environment
3. Deploy using Docker Compose:
   ```bash
   make up
   # Or: docker compose -f docker-compose/docker-compose.yaml up -d
   ```

## Deployment Behind Reverse Proxy

The application is designed to be deployed behind a reverse proxy (e.g., Traefik, Nginx) with the following considerations:

### Architecture

```
Internet → Reverse Proxy (Traefik) → Application
                                    ├─ Frontend (nginx on port 80)
                                    ├─ Envoy Proxy (port 50052)
                                    └─ gRPC Server (port 50051, internal)
```

### Path Prefix Routing

When deploying behind a reverse proxy with path prefix routing (e.g., `https://yourdomain.com/eternity2`), configure the `BASE_PATH` environment variable:

#### Example: Traefik with Path Prefix

```yaml
# docker-compose/docker-compose.yaml
services:
  frontend:
    environment:
      - BASE_PATH=/eternity2
      - SERVER_BASE_URL=https://yourdomain.com/eternity2-api
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.eternity2-frontend.rule=PathPrefix(`/eternity2`)"
      - "traefik.http.routers.eternity2-frontend.middlewares=eternity2-strip"
      - "traefik.http.middlewares.eternity2-strip.stripprefix.prefixes=/eternity2"
      - "traefik.http.services.eternity2-frontend.loadbalancer.server.port=80"

  envoy:
    environment:
      - SOLVER_API=grpc-server
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.eternity2-api.rule=PathPrefix(`/eternity2-api`)"
      - "traefik.http.routers.eternity2-api.middlewares=eternity2-api-strip"
      - "traefik.http.middlewares.eternity2-api-strip.stripprefix.prefixes=/eternity2-api"
      - "traefik.http.services.eternity2-api.loadbalancer.server.port=50052"
```

**Important Notes:**
- The reverse proxy should **strip the path prefix** before forwarding requests to the containers
- The frontend container will handle routing internally using React Router with the `basename` set to the `BASE_PATH`
- `SERVER_BASE_URL` should point to the public URL where the Envoy proxy is accessible

### Port Configuration

#### Default Ports (for local/direct access)
- **Frontend**: 80
- **Envoy Proxy**: 50052
- **gRPC Server**: 50051 (internal only, not exposed)

#### Production Behind Reverse Proxy

In production, you typically **should not expose ports 50052 or 50051 directly** to the internet. Instead:

1. Remove port mappings from `docker-compose/docker-compose.yaml`:
   ```yaml
   services:
     envoy:
       # Remove this in production:
       # ports:
       #   - "50052:50052"

     frontend:
       # Remove this in production:
       # ports:
       #   - "80:80"
   ```

2. Let the reverse proxy handle all external traffic on ports 80/443
3. Use Docker networking for internal communication between containers

#### Example Production docker-compose/docker-compose.yaml

```yaml
services:
  grpc-server:
    image: your-registry.com/eternity2/grpc-server:latest
    networks:
      - eternity2
    # No exposed ports - internal only

  envoy:
    image: your-registry.com/eternity2/envoy:latest
    environment:
      - SOLVER_API=grpc-server
    networks:
      - eternity2
      - traefik  # External network for reverse proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.eternity2-api.rule=PathPrefix(`/eternity2-api`)"
      - "traefik.http.routers.eternity2-api.tls=true"
      - "traefik.http.routers.eternity2-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.eternity2-api.loadbalancer.server.port=50052"
      - "traefik.docker.network=traefik"

  frontend:
    image: your-registry.com/eternity2/frontend:latest
    environment:
      - SERVER_BASE_URL=https://yourdomain.com/eternity2-api
      - BASE_PATH=/eternity2
    networks:
      - eternity2
      - traefik  # External network for reverse proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.eternity2-frontend.rule=PathPrefix(`/eternity2`)"
      - "traefik.http.routers.eternity2-frontend.tls=true"
      - "traefik.http.routers.eternity2-frontend.tls.certresolver=letsencrypt"
      - "traefik.http.services.eternity2-frontend.loadbalancer.server.port=80"
      - "traefik.docker.network=traefik"

networks:
  eternity2:
    internal: true
  traefik:
    external: true
```

## Environment Variables

### Frontend Service

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SERVER_BASE_URL` | URL of the Envoy proxy (gRPC-Web gateway) | `http://localhost:50052` | Yes |
| `BASE_PATH` | Path prefix for deployment behind reverse proxy | `/eternity2` | No (default: `/`) |

### Envoy Service

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SOLVER_API` | Hostname of the gRPC server | `grpc-server` | Yes |

## Health Checks

You can verify the deployment by checking:

1. **Frontend**: Access the configured URL in a browser
2. **Envoy Proxy**: Check Envoy admin interface (if enabled) at `http://envoy:9901`
3. **gRPC Server**: Use grpcurl to test the gRPC endpoints

## Troubleshooting

### Frontend shows 404 errors for assets

**Cause**: `BASE_PATH` mismatch or reverse proxy not stripping the prefix correctly.

**Solution**:
- Verify `BASE_PATH` environment variable matches your deployment path
- Ensure reverse proxy is configured to strip the path prefix
- Check browser console for asset loading errors

### gRPC calls fail with CORS errors

**Cause**: Envoy proxy not accessible or CORS configuration issue.

**Solution**:
- Verify `SERVER_BASE_URL` points to the correct Envoy proxy URL
- Check Envoy CORS configuration in `envoy/envoy.yaml`
- Ensure reverse proxy is forwarding gRPC-Web requests correctly

### Cannot connect to backend

**Cause**: Network configuration or service discovery issue.

**Solution**:
- Verify all services are on the same Docker network
- Check service names match in environment variables
- Use `docker compose logs` to check for errors

## Security Considerations

1. **Do not expose port 50052 directly to the internet** - always use HTTPS via reverse proxy
2. **Use TLS termination** at the reverse proxy level
3. **Implement rate limiting** at the reverse proxy to prevent abuse
4. **Use secrets management** for sensitive environment variables
5. **Keep Docker images up to date** to patch security vulnerabilities

## Monitoring

Consider adding monitoring for:
- Container health and resource usage
- HTTP response times and error rates
- gRPC request metrics
- Nginx access and error logs

Recommended tools:
- Prometheus + Grafana for metrics
- ELK Stack or Loki for log aggregation
- Traefik dashboard for reverse proxy monitoring
