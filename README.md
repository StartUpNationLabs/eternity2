# Eternity2 Project

A web-based solver for the Eternity II puzzle, featuring a C++ high-performance solver backend and a React frontend.

## Overview

This project consists of three main components:

1. **gRPC Server** - High-performance C++ solver with gRPC API
2. **Envoy Proxy** - gRPC-Web gateway for browser access
3. **Frontend** - React-based web interface

The application is designed for:
- Local development and experimentation
- Production deployment behind reverse proxies (Traefik, Nginx)
- Educational and research purposes for constraint satisfaction problems

## Quick Start

### Using Docker (Recommended)

```bash
# Start the application
docker compose up -d

# Access the web interface
open http://localhost:80
```

The Envoy proxy (API gateway) is available at `http://localhost:50052`.

### Building from Source

```bash
# Install dependencies
make install

# Build all components
make build

# Or build Docker images
make docker-build
```

## Documentation

- **[BUILD.md](./BUILD.md)** - Complete build instructions for all components
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide and reverse proxy configuration
- **[DEPENDENCIES.md](./DEPENDENCIES.md)** - All required tools and dependencies

## Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────┐      ┌─────────────────┐
│    Frontend     │─────→│ Envoy Proxy  │─────→│   gRPC Server   │
│  (React/Nginx)  │      │  (gRPC-Web)  │      │ (C++ Solver)    │
└─────────────────┘      └──────────────┘      └─────────────────┘
     Port 80                 Port 50052            Port 50051
                                                   (internal)
```

## Project Structure

```
.
├── api/              # C++ gRPC server implementation
├── solver/           # Core solver algorithms (C++)
├── frontend/         # React web application
├── envoy/            # Envoy proxy configuration
├── tests/            # C++ unit tests
├── build-base/       # Docker base image with dependencies
└── Makefile          # Build automation
```

## Available Make Targets

```bash
make help              # Show all available targets
make build             # Build all components (C++ and frontend)
make test              # Run all tests
make docker-build      # Build all Docker images
make docker-push-all   # Push images to registry
make clean             # Clean all build artifacts
make info              # Show build configuration
```

## Environment Variables

### Frontend Service

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SERVER_BASE_URL` | URL of the Envoy proxy | `http://localhost:50052` | Yes |
| `BASE_PATH` | Path prefix for reverse proxy deployment | `/` | No |

### Envoy Service

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SOLVER_API` | Hostname of the gRPC server | `grpc-server` | Yes |

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Access the dev server at `http://localhost:5173` with hot-reloading.

### C++ Development

```bash
# Configure build
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake

# Build
cmake --build build -j$(nproc)

# Run tests
cd build && ctest --output-on-failure
```

## Production Deployment

### Building for Production

```bash
# Set your registry
export DOCKER_REGISTRY=your-registry.com/eternity2
export DOCKER_TAG=v1.0.0

# Build and push
make docker-build
make docker-push-all
```

### Deploying Behind Reverse Proxy

For deployment behind Traefik or Nginx with path prefix routing:

```bash
# Example: Deploy under /eternity2 path
export BASE_PATH=/eternity2
export SERVER_BASE_URL=https://yourdomain.com/eternity2-api

docker compose up -d
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed reverse proxy configuration.

## Requirements

### For Docker-only usage:
- Docker >= 20.10
- Docker Compose >= 2.0

### For local development:
- CMake >= 3.10
- C++ compiler with C++17 support
- Node.js >= 18.x
- vcpkg (C++ package manager)

See [DEPENDENCIES.md](./DEPENDENCIES.md) for complete dependency information.

## Testing

```bash
# Run C++ tests
make test-cpp

# Or manually
cd build
ctest --output-on-failure
```

## Contributing

This project was developed as part of a Polytech Nice-Sophia educational initiative.

## License

See LICENSE file for details.

## Acknowledgments

- Terra Numerica (CNRS, Inria, Université Côte d'Azur)
- Polytech Nice-Sophia
- StartUpNation Labs

## Support

For deployment assistance or issues:
- Check the documentation in `BUILD.md` and `DEPLOYMENT.md`
- Review `DEPENDENCIES.md` for dependency issues
- Open an issue on the GitHub repository
