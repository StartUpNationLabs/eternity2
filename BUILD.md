# Build Guide

This document provides detailed instructions for building the Eternity2 project from source. The project consists of C++ components (solver and gRPC API) and a React frontend.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Building Components Separately](#building-components-separately)
- [Docker Build Process](#docker-build-process)
- [Build Troubleshooting](#build-troubleshooting)

## Prerequisites

Before building, ensure you have all required dependencies installed. See [DEPENDENCIES.md](./DEPENDENCIES.md) for detailed installation instructions.

**Minimum requirements:**
- CMake >= 3.10
- C++ compiler with C++17 support (GCC >= 7.0 or Clang >= 5.0)
- Node.js >= 18.x
- npm >= 9.x
- vcpkg (for C++ dependencies)
- Docker and Docker Compose (for Docker builds)

## Quick Start

### Option 1: Docker Build (Recommended)

The easiest way to build everything is using Docker:

```bash
# Build all Docker images
make docker-build

# This will build:
# - Base image with C++ dependencies
# - gRPC Server image
# - Frontend image
# - Envoy proxy image
```

### Option 2: Local Build

Build all components locally:

```bash
# Install dependencies first
make install

# Build everything (C++ and frontend)
make build
```

## Building Components Separately

### Building C++ Components (Solver + API)

The C++ components use CMake as the build system and vcpkg for dependency management.

#### Step 1: Install C++ Dependencies

```bash
# Ensure VCPKG_ROOT is set
export VCPKG_ROOT=/path/to/vcpkg

# Install dependencies via vcpkg
vcpkg install
```

Dependencies installed:
- protobuf (Protocol Buffers)
- asio-grpc (Async gRPC library)
- libunifex (Unified Executors)
- catch2 (Testing framework)
- spdlog (Logging)
- hiredis (Redis client)
- redis-plus-plus (C++ Redis client)

#### Step 2: Configure with CMake

```bash
# Configure the build with vcpkg toolchain
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake

# Or use the Makefile
make build-cpp
```

#### Step 3: Build

```bash
# Build using CMake
cmake --build build -j$(nproc)

# Or use the Makefile
make build-cpp
```

#### Build Output

- **Solver library**: `build/solver/libsolver_lib.a`
- **gRPC Server**: `build/api/asio-grpc-server`
- **Tests**: `build/tests/tests` (if Catch2 is available)

### Building the Frontend

The frontend is a React application built with Vite.

#### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

#### Step 2: Build

```bash
# Production build
npm run build

# Or from project root
make build-frontend
```

#### Build Output

The production build will be created in `frontend/dist/`:
- `index.html` - Entry point
- `assets/` - JavaScript, CSS, and other static assets

#### Development Build

For development with hot-reloading:

```bash
cd frontend
npm run dev

# Or from project root
make dev-frontend
```

This starts a development server at `http://localhost:5173`.

## Docker Build Process

### Understanding the Multi-Stage Build

Each component uses a multi-stage Docker build for optimization:

#### 1. Base Image (`build-base/Dockerfile`)

Contains all C++ build dependencies and vcpkg packages:

```bash
# Build the base image
make docker-build-base

# Or manually:
docker build -t ghcr.io/startupnationlabs/eternity2/base:latest \
  -f build-base/Dockerfile \
  build-base
```

This image is used as the build environment for the API server.

#### 2. gRPC Server Image (`api/Dockerfile`)

```bash
# Build the gRPC server image
make docker-build-api

# Or manually:
docker build -t ghcr.io/startupnationlabs/eternity2/grpc-server:latest \
  -f api/Dockerfile \
  .
```

**Build stages:**
1. Uses base image for building
2. Copies source code
3. Runs CMake configuration and build
4. Creates minimal final image with only the binary (uses `FROM scratch`)

#### 3. Frontend Image (`frontend/Dockerfile`)

```bash
# Build the frontend image
make docker-build-frontend

# Or manually:
docker build -t ghcr.io/startupnationlabs/eternity2/frontend:latest \
  -f frontend/Dockerfile \
  frontend
```

**Build stages:**
1. Node.js build stage: Installs deps and builds React app
2. Production stage: Nginx with built assets
3. Includes entrypoint script for runtime configuration

#### 4. Envoy Proxy Image (`envoy/Dockerfile`)

```bash
# Build the Envoy image
make docker-build-envoy

# Or manually:
docker build -t ghcr.io/startupnationlabs/eternity2/envoy:latest \
  -f envoy/Dockerfile \
  envoy
```

Based on official Envoy image with custom configuration.

### Customizing Docker Registry

To build for your own registry:

```bash
export DOCKER_REGISTRY=your-registry.com/your-project
export DOCKER_TAG=v1.0.0

make docker-build
```

### Building with Docker Compose

You can also use Docker Compose to build images:

1. Edit `docker-compose.yaml` and uncomment the `build` sections
2. Run:
   ```bash
   docker compose build
   ```

## Build Artifacts

### Local Build

After a successful local build, you'll have:

```
build/
├── api/
│   └── asio-grpc-server          # gRPC server binary
├── solver/
│   └── libsolver_lib.a           # Solver library
└── tests/
    └── tests                      # Test binary (if Catch2 available)

frontend/dist/
├── index.html                     # Frontend entry point
└── assets/                        # Frontend assets
    ├── index-[hash].js
    ├── index-[hash].css
    └── ...
```

### Docker Build

After building Docker images:

```bash
docker images | grep eternity2
```

You should see:
- `eternity2/base:latest`
- `eternity2/grpc-server:latest`
- `eternity2/frontend:latest`
- `eternity2/envoy:latest`

## Running Tests

### C++ Tests

```bash
# Build and run tests
make test-cpp

# Or manually:
cd build
ctest --output-on-failure
```

Tests are built using the Catch2 framework. If Catch2 is not available via vcpkg, tests will be skipped during build.

### Frontend Tests

Currently, frontend tests are not configured. To add tests:

```bash
cd frontend
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

## Build Troubleshooting

### CMake can't find Catch2

**Problem:**
```
Could not find a package configuration file provided by "Catch2"
```

**Solution:**
Ensure you're using the vcpkg toolchain:
```bash
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
```

Or use Docker build which handles this automatically.

### vcpkg installation fails

**Problem:**
vcpkg can't install packages or times out.

**Solution:**
1. Check internet connection
2. Update vcpkg:
   ```bash
   cd $VCPKG_ROOT
   git pull
   ./bootstrap-vcpkg.sh
   ```
3. Try installing packages individually:
   ```bash
   vcpkg install protobuf asio-grpc libunifex catch2 spdlog hiredis redis-plus-plus
   ```

### Frontend build fails with Node.js errors

**Problem:**
```
Error: Cannot find module 'vite'
```

**Solution:**
1. Ensure Node.js >= 18.x:
   ```bash
   node --version
   ```
2. Delete and reinstall dependencies:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Docker build is very slow

**Possible causes:**
1. Building base image compiles all vcpkg packages (can take 30+ minutes first time)
2. No Docker build cache

**Solutions:**
1. Use pre-built base image: `ghcr.io/startupnationlabs/eternity2/base:latest`
2. Build base image once and reuse:
   ```bash
   make docker-build-base
   # Cache is saved, subsequent builds are faster
   ```
3. Use Docker BuildKit for better caching:
   ```bash
   export DOCKER_BUILDKIT=1
   make docker-build
   ```

### Permission denied errors during build

**Problem:**
Build artifacts have wrong permissions.

**Solution:**
This usually happens with Docker builds. Add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

## Clean Build

To clean all build artifacts:

```bash
# Clean everything
make clean

# Clean only C++ artifacts
make clean-cpp

# Clean only frontend artifacts
make clean-frontend
```

## Build Performance Tips

1. **Use parallel builds:**
   ```bash
   cmake --build build -j$(nproc)  # Use all CPU cores
   ```

2. **Use ccache for C++ compilation:**
   ```bash
   sudo apt-get install ccache
   export CMAKE_CXX_COMPILER_LAUNCHER=ccache
   ```

3. **Disable tests if not needed:**
   ```bash
   cmake -B build -S . -DBUILD_TESTING=OFF
   ```

4. **Use Docker BuildKit:**
   ```bash
   export DOCKER_BUILDKIT=1
   ```

## Continuous Integration

For CI/CD pipelines, use the Docker build approach:

```bash
#!/bin/bash
set -e

# Build all images
make docker-build

# Tag for your registry
docker tag eternity2/grpc-server:latest your-registry.com/eternity2/grpc-server:$GIT_SHA
docker tag eternity2/frontend:latest your-registry.com/eternity2/frontend:$GIT_SHA
docker tag eternity2/envoy:latest your-registry.com/eternity2/envoy:$GIT_SHA

# Push to registry
docker push your-registry.com/eternity2/grpc-server:$GIT_SHA
docker push your-registry.com/eternity2/frontend:$GIT_SHA
docker push your-registry.com/eternity2/envoy:$GIT_SHA
```

## Next Steps

After building:
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment instructions
- See [README.md](./README.md) for usage and project overview
- See [DEPENDENCIES.md](./DEPENDENCIES.md) for dependency information
