cmake_minimum_required(VERSION 3.10)
project(eternity2)

# Enforce out-of-source builds
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-source builds are not allowed. Please create a build directory and run cmake from there.\nExample: mkdir build && cd build && cmake ..")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")

add_subdirectory(solvers/v1)
add_subdirectory(solvers/v2)
add_subdirectory(solvers/benchmark)

# API is optional - only build if dependencies are available
find_package(asio-grpc CONFIG QUIET)
if(asio-grpc_FOUND)
    message(STATUS "asio-grpc found - building API")
    add_subdirectory(api)
else()
    message(STATUS "asio-grpc not found - skipping API")
endif()

# Tests are optional - only build if Catch2 is available
find_package(Catch2 CONFIG QUIET)
if(Catch2_FOUND)
    message(STATUS "Catch2 found - building tests")
    enable_testing()
    add_subdirectory(tests)
else()
    message(WARNING "Catch2 not found - skipping tests. Install via vcpkg or use -DCMAKE_TOOLCHAIN_FILE")
endif()