# Project Dependencies

This document lists all the tooling and dependencies required to build and run the Eternity2 project.

## System Requirements

### Required Build Tools

#### For C++ Backend (API/Solver)
- **CMake** >= 3.10
  - Purpose: Build system generator
  - Installation:
    - Ubuntu/Debian: `sudo apt-get install cmake`
    - macOS: `brew install cmake`
    - Arch Linux: `sudo pacman -S cmake`

- **C++ Compiler** with C++17 support
  - GCC >= 7.0 or Clang >= 5.0
  - Installation:
    - Ubuntu/Debian: `sudo apt-get install build-essential`
    - macOS: `xcode-select --install`
    - Arch Linux: `sudo pacman -S base-devel`

- **vcpkg** (C++ package manager)
  - Purpose: Manages C++ dependencies
  - Installation:
    ```bash
    git clone https://github.com/microsoft/vcpkg.git
    ./vcpkg/bootstrap-vcpkg.sh
    export VCPKG_ROOT=/path/to/vcpkg
    export PATH=$VCPKG_ROOT:$PATH
    ```

#### For Frontend
- **Node.js** >= 18.x (LTS recommended)
  - Purpose: JavaScript runtime for building the React frontend
  - Installation:
    - Ubuntu/Debian:
      ```bash
      curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
      sudo apt-get install -y nodejs
      ```
    - macOS: `brew install node`
    - Arch Linux: `sudo pacman -S nodejs npm`

- **npm** (comes with Node.js)
  - Purpose: JavaScript package manager
  - Version: >= 9.x

#### For Docker Deployment
- **Docker** >= 20.10
  - Purpose: Container runtime
  - Installation: https://docs.docker.com/engine/install/

- **Docker Compose** >= 2.0
  - Purpose: Multi-container orchestration
  - Installation: https://docs.docker.com/compose/install/

### Optional Development Tools
- **Git** - Version control
- **Make** - Build automation (for using the project Makefile)

## C++ Dependencies (Managed by vcpkg)

The following C++ libraries are automatically installed via vcpkg:

- **protobuf** - Protocol Buffers for data serialization
- **asio-grpc** - Asynchronous gRPC library
- **libunifex** - Unified Executors library
- **catch2** - C++ testing framework
- **Custom logger** - Simple logging utility (in `solvers/common/logger.h`)
- **hiredis** - Redis C client library
- **redis-plus-plus** - C++ client for Redis

These are defined in `vcpkg.json` and installed automatically during the build process.

## Frontend Dependencies (Managed by npm)

All frontend dependencies are defined in `frontend/package.json` and installed via:
```bash
cd frontend
npm install
```

Key dependencies include:
- **React** 18.x - UI framework
- **Vite** 5.x - Build tool and dev server
- **TypeScript** 5.x - Type-safe JavaScript
- **Material-UI** - Component library
- **gRPC-Web** - Browser gRPC client
- **Tailwind CSS** - Utility-first CSS framework

## Verification

To verify all dependencies are installed correctly:

### Check C++ Build Tools
```bash
cmake --version
g++ --version  # or clang++ --version
vcpkg --version
```

### Check Frontend Tools
```bash
node --version
npm --version
```

### Check Docker Tools
```bash
docker --version
docker compose version
```

## Troubleshooting

### Catch2 Not Found Error
If you encounter the error:
```
Could not find a package configuration file provided by "Catch2"
```

This is expected when building locally without vcpkg. Use one of the following solutions:

1. **Use vcpkg toolchain** (recommended):
   ```bash
   cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake
   ```

2. **Build using Docker** (no local C++ toolchain needed):
   ```bash
   make docker-build
   ```

3. **Install Catch2 system-wide**:
   ```bash
   vcpkg install catch2
   # Then add to CMAKE_PREFIX_PATH or Catch2_DIR
   ```

### Node.js Version Issues
Ensure you're using Node.js 18.x or higher:
```bash
node --version  # Should be v18.x.x or higher
```

If you need multiple Node.js versions, consider using `nvm` (Node Version Manager).

## Platform-Specific Notes

### Linux
- The project is primarily developed and tested on Debian-based distributions
- All dependencies are available through standard package managers
- On some distributions, you may need to install `gettext-base` for envsubst:
  ```bash
  sudo apt-get install gettext-base
  ```

### macOS
- Ensure Xcode Command Line Tools are installed
- Use Homebrew for most dependencies
- Some vcpkg packages may take longer to build on Apple Silicon (M1/M2)

### Windows
- Not officially supported but may work with WSL2 (Windows Subsystem for Linux)
- Native Windows build not tested

## Docker-Only Development

If you prefer not to install all dependencies locally, you can use Docker exclusively:

```bash
# Build all images
make docker-build

# Run the application
docker compose up
```

This approach only requires Docker and Docker Compose to be installed.
