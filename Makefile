# Eternity2 Project Makefile
# This Makefile provides targets for building all project artifacts

.PHONY: all clean help
.PHONY: build build-cpp build-frontend
.PHONY: docker-build docker-build-base docker-build-base-build docker-build-api docker-build-frontend docker-build-envoy
.PHONY: docker-push docker-push-all
.PHONY: test test-cpp
.PHONY: dev dev-frontend

# Configuration
VCPKG_ROOT ?= $(HOME)/vcpkg
CMAKE ?= cmake
DOCKER ?= docker
DOCKER_COMPOSE ?= docker compose
NPM ?= npm

# Docker image configuration
DOCKER_REGISTRY ?= ghcr.io/startupnationlabs/eternity2
DOCKER_TAG ?= latest

# Build directories
BUILD_DIR := build
FRONTEND_DIR := frontend
API_DIR := api
ENVOY_DIR := envoy
BUILD_BASE_DIR := build-base

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

all: build ## Build everything (C++ and frontend)

clean: clean-cpp clean-frontend ## Clean all build artifacts
	@echo "All build artifacts cleaned"

##@ Local Development

build: build-cpp build-frontend ## Build C++ binaries and frontend bundle

build-cpp: ## Build C++ components (solver and API)
	@echo "Building C++ components..."
	@if [ -z "$$VCPKG_ROOT" ]; then \
		echo "WARNING: VCPKG_ROOT not set. Using system-installed dependencies."; \
		$(CMAKE) -B $(BUILD_DIR) -S . ; \
	else \
		echo "Using vcpkg from: $$VCPKG_ROOT"; \
		$(CMAKE) -B $(BUILD_DIR) -S . -DCMAKE_TOOLCHAIN_FILE=$$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake ; \
	fi
	$(CMAKE) --build $(BUILD_DIR) -j$(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
	@echo "C++ build complete"

build-frontend: ## Build frontend bundle
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && $(NPM) install
	cd $(FRONTEND_DIR) && $(NPM) run build
	@echo "Frontend build complete"

clean-cpp: ## Clean C++ build artifacts
	@echo "Cleaning C++ build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf CMakeCache.txt CMakeFiles CTestTestfile.cmake Makefile.cmake
	@echo "C++ build artifacts cleaned"

clean-frontend: ## Clean frontend build artifacts
	@echo "Cleaning frontend build artifacts..."
	cd $(FRONTEND_DIR) && rm -rf dist node_modules
	@echo "Frontend build artifacts cleaned"

##@ Testing

test: test-cpp ## Run all tests

test-cpp: build-cpp ## Run C++ tests
	@echo "Running C++ tests..."
	@if [ -f "$(BUILD_DIR)/tests/tests" ]; then \
		cd $(BUILD_DIR) && ctest --output-on-failure ; \
	else \
		echo "Tests not built (Catch2 may not be available)"; \
		exit 0; \
	fi

##@ Docker Operations

docker-build: docker-build-base docker-build-api docker-build-frontend docker-build-envoy ## Build all Docker images

docker-build-base: ## Pull base Docker image with dependencies
	@echo "Pulling base image..."
	$(DOCKER) pull $(DOCKER_REGISTRY)/base:$(DOCKER_TAG) || \
		(echo "Warning: Failed to pull base image. You may need to build it first with: make docker-build-base-build" && exit 1)
	@echo "Base image pulled: $(DOCKER_REGISTRY)/base:$(DOCKER_TAG)"

docker-build-base-build: ## Build base Docker image with dependencies (use docker-build-base to pull instead)
	@echo "Building base image..."
	$(DOCKER) build -t $(DOCKER_REGISTRY)/base:$(DOCKER_TAG) \
		-f $(BUILD_BASE_DIR)/Dockerfile \
		$(BUILD_BASE_DIR)
	@echo "Base image built: $(DOCKER_REGISTRY)/base:$(DOCKER_TAG)"

docker-build-api: ## Build API Docker image
	@echo "Building API image..."
	$(DOCKER) build -t $(DOCKER_REGISTRY)/grpc-server:$(DOCKER_TAG) \
		-f $(API_DIR)/Dockerfile \
		.
	@echo "API image built: $(DOCKER_REGISTRY)/grpc-server:$(DOCKER_TAG)"

docker-build-frontend: ## Build frontend Docker image
	@echo "Building frontend image..."
	$(DOCKER) build -t $(DOCKER_REGISTRY)/frontend:$(DOCKER_TAG) \
		-f $(FRONTEND_DIR)/Dockerfile \
		$(FRONTEND_DIR)
	@echo "Frontend image built: $(DOCKER_REGISTRY)/frontend:$(DOCKER_TAG)"

docker-build-envoy: ## Build Envoy proxy Docker image
	@echo "Building Envoy image..."
	$(DOCKER) build -t $(DOCKER_REGISTRY)/envoy:$(DOCKER_TAG) \
		-f $(ENVOY_DIR)/Dockerfile \
		$(ENVOY_DIR)
	@echo "Envoy image built: $(DOCKER_REGISTRY)/envoy:$(DOCKER_TAG)"

docker-push-all: docker-push-base docker-push-api docker-push-frontend docker-push-envoy ## Push all Docker images to registry

docker-push-base: ## Push base image to registry
	@echo "Pushing base image..."
	$(DOCKER) push $(DOCKER_REGISTRY)/base:$(DOCKER_TAG)

docker-push-api: ## Push API image to registry
	@echo "Pushing API image..."
	$(DOCKER) push $(DOCKER_REGISTRY)/grpc-server:$(DOCKER_TAG)

docker-push-frontend: ## Push frontend image to registry
	@echo "Pushing frontend image..."
	$(DOCKER) push $(DOCKER_REGISTRY)/frontend:$(DOCKER_TAG)

docker-push-envoy: ## Push Envoy image to registry
	@echo "Pushing Envoy image..."
	$(DOCKER) push $(DOCKER_REGISTRY)/envoy:$(DOCKER_TAG)

##@ Docker Compose Operations

DOCKER_COMPOSE_DIR := docker-compose
DOCKER_COMPOSE_FILE := $(DOCKER_COMPOSE_DIR)/docker-compose.yaml

up: ## Start all services with docker-compose
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

down: ## Stop all services
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down

logs: ## Show logs from all services
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f

restart: down up ## Restart all services

##@ Development

dev-frontend: ## Start frontend development server
	@echo "Starting frontend dev server..."
	cd $(FRONTEND_DIR) && $(NPM) run dev

install: ## Install all dependencies (local development)
	@echo "Installing C++ dependencies via vcpkg..."
	@if [ -z "$$VCPKG_ROOT" ]; then \
		echo "ERROR: VCPKG_ROOT not set. Please set it to your vcpkg installation path."; \
		exit 1; \
	fi
	vcpkg install
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(NPM) install
	@echo "All dependencies installed"

##@ Release

release: clean docker-build docker-push-all ## Clean, build, and push all Docker images

##@ Information

info: ## Show build configuration
	@echo "Build Configuration:"
	@echo "  VCPKG_ROOT:      $${VCPKG_ROOT:-Not set}"
	@echo "  CMAKE:           $(CMAKE)"
	@echo "  NPM:             $(NPM)"
	@echo "  DOCKER:          $(DOCKER)"
	@echo "  DOCKER_COMPOSE:  $(DOCKER_COMPOSE)"
	@echo "  DOCKER_REGISTRY: $(DOCKER_REGISTRY)"
	@echo "  DOCKER_TAG:      $(DOCKER_TAG)"
	@echo ""
	@echo "Tool versions:"
	@$(CMAKE) --version 2>/dev/null | head -n1 || echo "  cmake: not found"
	@node --version 2>/dev/null | sed 's/^/  node: /' || echo "  node: not found"
	@$(NPM) --version 2>/dev/null | sed 's/^/  npm: /' || echo "  npm: not found"
	@$(DOCKER) --version 2>/dev/null || echo "  docker: not found"
	@$(DOCKER_COMPOSE) version 2>/dev/null || echo "  docker-compose: not found"
