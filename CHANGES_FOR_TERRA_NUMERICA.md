# Changes for Terra Numerica Deployment

This document summarizes all changes made to the Eternity2 project to address the requirements from Eric Pascual and the Terra Numerica team for production deployment.

**Date:** December 2025
**Requester:** Eric Pascual (Terra Numerica)
**Purpose:** Enable autonomous deployment and maintenance of the Eternity2 application

## Summary of Changes

All requirements mentioned in the email exchanges have been addressed:

1. ✅ **Documentation of dependencies** - Complete tooling requirements documented
2. ✅ **Reproducible build process** - Comprehensive Makefile created
3. ✅ **Fixed Catch2 dependency issue** - Tests now optional when Catch2 unavailable
4. ✅ **Docker build configuration** - Build contexts and instructions provided
5. ✅ **Path prefix routing support** - Full support for deployment behind Traefik

## New Files Created

### Documentation

1. **`DEPENDENCIES.md`**
   - Complete list of all required build tools (CMake, C++ compiler, Node.js, vcpkg, Docker)
   - Installation instructions for major Linux distributions and macOS
   - Troubleshooting guide for common dependency issues
   - Platform-specific notes

2. **`BUILD.md`**
   - Detailed build instructions for C++ components and frontend
   - Docker build process explanation with multi-stage builds
   - Build troubleshooting guide
   - Performance optimization tips
   - CI/CD integration examples

3. **`DEPLOYMENT.md`**
   - Production deployment guide
   - Traefik reverse proxy configuration with examples
   - Path prefix routing setup
   - Port configuration for production (addressing the port 50052 concern)
   - Security considerations
   - Environment variable reference

4. **`CHANGES_FOR_TERRA_NUMERICA.md`** (this file)
   - Summary of all changes made
   - Migration guide for deployment

### Build Configuration

5. **`Makefile`** (replaced CMake-generated version)
   - Comprehensive build automation for all components
   - Targets for: building, testing, Docker image creation, registry push
   - Self-documenting with `make help`
   - Support for custom Docker registries
   - Examples:
     ```bash
     make build              # Build all components
     make docker-build       # Build all Docker images
     make docker-push-all    # Push to registry
     make test               # Run tests
     make clean              # Clean build artifacts
     ```

6. **`docker-compose.build.yaml`**
   - Configuration for building images from source
   - Alternative to using pre-built images
   - Ensures complete build autonomy

7. **`docker-compose.prod.yaml`**
   - Production-ready configuration with Traefik labels
   - No exposed ports (all traffic via reverse proxy)
   - Health checks for all services
   - Proper network isolation

8. **`.env.example`**
   - Template for environment variables
   - Documented configuration options
   - Production deployment examples

## Modified Files

### Core Changes

9. **`CMakeLists.txt`**
   - **Issue Fixed:** Catch2 dependency error when building without vcpkg
   - **Solution:** Made tests optional - builds successfully without Catch2
   - **Impact:** Can now run `cmake .` without errors, tests are skipped gracefully

10. **`docker-compose.yaml`**
    - Added commented build contexts for all services
    - Added `BASE_PATH` environment variable support
    - Added documentation comments
    - Can now be used for both pre-built and source builds

### Frontend Changes

11. **`frontend/vite.config.ts`**
    - Added support for `BASE_PATH` environment variable
    - Enables building for specific path prefixes
    - Configured with `base` option for proper asset paths

12. **`frontend/src/main.tsx`**
    - Added runtime base path detection from `/env` file
    - React Router configured with `basename` parameter
    - Supports dynamic path prefix routing

13. **`frontend/docker-entrypoint.sh`**
    - Enhanced to write `BASE_PATH` to environment file
    - Dynamic nginx configuration based on `BASE_PATH`
    - Handles both root and prefixed deployments
    - Supports Traefik's path stripping

14. **`README.md`**
    - Complete rewrite with project overview
    - Quick start guide
    - Links to new documentation files
    - Architecture diagram
    - Make targets reference

## How These Changes Address Requirements

### 1. Dependency Documentation (Eric's first request)

**Request:**
> "documenter les dépendances du projet en termes d'outillage"

**Solution:**
- `DEPENDENCIES.md` provides complete tooling requirements
- Installation commands for all platforms
- Verification steps to check installations
- Troubleshooting section

### 2. Catch2 Build Error (Eric's CMake issue)

**Request/Issue:**
```
CMake Error: Could not find a package configuration file provided by "Catch2"
```

**Solution:**
- Modified `CMakeLists.txt` to make tests optional
- Graceful degradation when Catch2 is unavailable
- Clear warning message when tests are skipped
- Full instructions in `BUILD.md` for proper vcpkg usage

### 3. Reproducible Build Process

**Request:**
> "nous avons besoin de tous les éléments nécessaires à notre autonomie"
> "Makefile général contenant toutes les targets pour la génération des binaires et images Docker"

**Solution:**
- Comprehensive `Makefile` with all build targets:
  - `make build` - Build C++ and frontend locally
  - `make docker-build` - Build all Docker images
  - `make docker-push-all` - Push to any registry
  - `make test` - Run all tests
  - `make clean` - Clean everything
- `BUILD.md` documents entire build process
- `docker-compose.build.yaml` for source builds

### 4. Docker Image Build Configuration

**Request:**
> "le projet ne comporte aucune indication ni Makefile concernant le build des différents artefacts"

**Solution:**
- Makefile with Docker build targets
- `docker-compose.build.yaml` with build contexts
- Commented build sections in main `docker-compose.yaml`
- Instructions for building and pushing to custom registry
- `BUILD.md` explains multi-stage Docker builds

### 5. Path Prefix Routing for Traefik

**Request:**
> "le routage est réalisé par le biais d'un path prefix"
> "La variable d'environnement SERVER_BASE_URL qui sert de racine à la construction des URLs publiques"

**Solution:**
- Added `BASE_PATH` environment variable throughout the stack
- Frontend supports dynamic base path at build and runtime
- Nginx configuration adapts to path prefix
- React Router configured with basename
- `docker-compose.prod.yaml` includes Traefik configuration examples
- `DEPLOYMENT.md` provides complete reverse proxy setup guide

### 6. Port 50052 Exposure Issue

**Request:**
> "exposer ce type de port sur Internet n'est pas vraiment envisageable"

**Solution:**
- `docker-compose.prod.yaml` doesn't expose any ports
- All traffic routed through Traefik on ports 80/443
- Documentation explains proper network configuration
- Security considerations documented in `DEPLOYMENT.md`

## Migration Guide for Terra Numerica

### Step 1: Review Documentation

1. Read `DEPENDENCIES.md` to understand what's needed on your server
2. Review `DEPLOYMENT.md` for Traefik configuration
3. Check `BUILD.md` if you need to build from source

### Step 2: Choose Deployment Method

**Option A: Use Pre-built Images (Simplest)**
```bash
# Use existing docker-compose.yaml with pre-built images
docker compose up -d
```

**Option B: Build from Source (Full Autonomy)**
```bash
# Clone the repository
git clone https://github.com/StartUpNationLabs/eternity2.git
cd eternity2

# Build all images
make docker-build

# Tag for your registry
export DOCKER_REGISTRY=your-registry.inria.fr/eternity2
export DOCKER_TAG=production

# Push to your registry
make docker-push-all
```

### Step 3: Configure for Production

1. Copy and customize environment:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. Example `.env` for Terra Numerica:
   ```env
   DOCKER_REGISTRY=your-registry.inria.fr/eternity2
   DOCKER_TAG=production
   BASE_PATH=/eternity2
   SERVER_BASE_URL=https://terranumerica.fr/eternity2-api
   SOLVER_API=grpc-server
   ```

3. Deploy with production configuration:
   ```bash
   docker compose -f docker-compose.prod.yaml up -d
   ```

### Step 4: Configure Traefik

The `docker-compose.prod.yaml` file includes Traefik labels. Ensure:

1. Traefik network `traefik-public` exists
2. Let's Encrypt cert resolver is configured
3. Adjust path prefixes if different from `/eternity2`

Example Traefik configuration is in `DEPLOYMENT.md`.

### Step 5: Verify Deployment

1. Check services are running:
   ```bash
   docker compose -f docker-compose.prod.yaml ps
   ```

2. Check logs:
   ```bash
   docker compose -f docker-compose.prod.yaml logs -f
   ```

3. Access the application at your configured URL

## Testing the Changes

### Local Testing (without Traefik)

```bash
# Standard deployment
docker compose up -d
# Access: http://localhost:80

# With path prefix
export BASE_PATH=/eternity2
export SERVER_BASE_URL=http://localhost:50052
docker compose -f docker-compose.build.yaml up -d
# Access: http://localhost:80/eternity2
```

### Production Testing (with Traefik)

Follow the configuration in `DEPLOYMENT.md` and `docker-compose.prod.yaml`.

## Answering Eric's Specific Questions

### "Quelles sont les différences entre les deux docker-compose?"

**Answer:** Now there are three docker-compose files:

1. **`docker-compose.yaml`** - Development/local use with pre-built images
2. **`docker-compose.build.yaml`** - Building all images from source
3. **`docker-compose.prod.yaml`** - Production deployment with Traefik

### "Lequel est destiné au déploiement en production?"

**Answer:** Use `docker-compose.prod.yaml` for production with Traefik.

### "Cela peut-il poser un problème avec le path prefix?"

**Answer:** No, full support has been implemented:
- Set `BASE_PATH` environment variable
- Frontend adapts automatically
- Traefik should strip the prefix (configured in labels)

### "Dispose-t-on d'un mécanisme de paramétrage externe?"

**Answer:** Yes, via environment variables:
- `BASE_PATH` for path prefix
- `SERVER_BASE_URL` for API endpoint
- Configured via `.env` file or docker-compose environment

## Maintaining the Project

### Building New Versions

```bash
# Update code from Git
git pull

# Build new images
export DOCKER_TAG=v1.1.0
make docker-build

# Push to your registry
make docker-push-all

# Deploy
docker compose -f docker-compose.prod.yaml pull
docker compose -f docker-compose.prod.yaml up -d
```

### Making Code Changes

1. Modify the code
2. Test locally:
   ```bash
   make build
   make test
   ```
3. Build Docker images:
   ```bash
   make docker-build
   ```
4. Deploy

### Troubleshooting

See the troubleshooting sections in:
- `DEPENDENCIES.md` - Dependency issues
- `BUILD.md` - Build problems
- `DEPLOYMENT.md` - Deployment and runtime issues

## Summary

All requirements from Eric Pascual have been addressed:

- ✅ Complete dependency documentation
- ✅ Reproducible build system with Makefile
- ✅ Docker build configurations
- ✅ Path prefix routing support
- ✅ No requirement to expose port 50052
- ✅ Full autonomy for Terra Numerica team

The project is now production-ready for deployment on Terra Numerica infrastructure with complete documentation for maintenance and future development.

## Contact

For questions about these changes:
- Review the documentation files first
- Check the troubleshooting sections
- Refer to the original email thread with Eric Pascual

## Next Steps

1. Review this document and the new documentation
2. Test the build process on a Terra Numerica server
3. Configure Traefik according to `DEPLOYMENT.md`
4. Deploy with `docker-compose.prod.yaml`
5. Verify the application is accessible and functional
