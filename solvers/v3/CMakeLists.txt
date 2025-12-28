cmake_minimum_required(VERSION 3.10)
project(eternity2_solver_v3)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

include(CheckCXXCompilerFlag)

# =============================================================================
# SIMD Detection and Configuration
# =============================================================================
if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm|aarch64|ARM64")
    set(ETERNITY2_SIMD_TYPE "NEON")
    message(STATUS "V3 Target architecture: ARM")
    check_cxx_compiler_flag("-march=armv8-a+simd" HAS_ARM_SIMD)
    if(HAS_ARM_SIMD)
        set(V3_ARCH_FLAGS "-march=armv8-a+simd")
        message(STATUS "V3 SIMD: ARM NEON enabled")
    endif()
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    message(STATUS "V3 Target architecture: x86_64")
    check_cxx_compiler_flag("-mavx512f -mavx512bw" HAS_AVX512)
    check_cxx_compiler_flag("-mavx2" HAS_AVX2)
    check_cxx_compiler_flag("-march=native" HAS_MARCH_NATIVE)

    if(HAS_AVX512)
        set(ETERNITY2_SIMD_TYPE "AVX512")
        set(V3_ARCH_FLAGS "-mavx512f -mavx512bw")
        message(STATUS "V3 SIMD: AVX-512 enabled")
    elseif(HAS_AVX2)
        set(ETERNITY2_SIMD_TYPE "AVX2")
        set(V3_ARCH_FLAGS "-mavx2")
        message(STATUS "V3 SIMD: AVX2 enabled")
    elseif(HAS_MARCH_NATIVE)
        set(ETERNITY2_SIMD_TYPE "NATIVE")
        set(V3_ARCH_FLAGS "-march=native")
        message(STATUS "V3 SIMD: Using native architecture")
    else()
        set(ETERNITY2_SIMD_TYPE "SCALAR")
        message(STATUS "V3 SIMD: Scalar fallback (no SIMD)")
    endif()
else()
    set(ETERNITY2_SIMD_TYPE "SCALAR")
    message(STATUS "V3 SIMD: Scalar fallback (unknown architecture)")
endif()

# =============================================================================
# Compiler Flags - Aggressive Optimization for HPC
# =============================================================================
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # Base optimization flags
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

    # Architecture-specific optimizations
    if(V3_ARCH_FLAGS)
        set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} ${V3_ARCH_FLAGS}")
    endif()

    # Additional performance flags
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -funroll-loops -ffast-math")

    # Link-Time Optimization (LTO) for cross-TU inlining
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)

    # Debug flags
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
endif()

# Export SIMD type as compile definition
add_compile_definitions(ETERNITY2_SIMD_TYPE_${ETERNITY2_SIMD_TYPE})

# Find Threads package for parallel solver
find_package(Threads REQUIRED)

# =============================================================================
# V3 DLX Solver Library
# =============================================================================
set(SOLVER_V3_SOURCES
    dlx/dlx_matrix.cpp
    solver/dlx_solver.cpp
    parallel/parallel_dlx_solver.cpp
)

set(SOLVER_V3_HEADERS
    dlx/dlx_node.h
    dlx/dlx_matrix.h
    solver/dlx_solver.h
    parallel/parallel_dlx_solver.h
    config/solver_config.h
)

# Create solver_v3 library
add_library(solver_v3_lib STATIC ${SOLVER_V3_SOURCES} ${SOLVER_V3_HEADERS})

# Include directories
target_include_directories(solver_v3_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/..  # Add solvers/ to include path for "common/types.h" and "v1/board.h"
)

# Link to v1 solver_lib for shared types (Piece, Board, etc.)
target_link_libraries(solver_v3_lib PUBLIC solver_lib Threads::Threads)

# Disable logging in library for performance
target_compile_definitions(solver_v3_lib PRIVATE DISABLE_LOGGING)

# =============================================================================
# Common Utilities
# =============================================================================
set(COMMON_SOURCES
    ../common/piece_utils.cpp
    ../common/piece_loader.cpp
)

# =============================================================================
# V3 Executable
# =============================================================================
add_executable(SolverV3 main.cpp ${COMMON_SOURCES})
target_include_directories(SolverV3 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/..)
target_link_libraries(SolverV3 solver_v3_lib)

# Enable logging for executable
target_compile_options(SolverV3 PRIVATE -UDISABLE_LOGGING)

message(STATUS "Building Eternity II Solver v3 - Dancing Links (DLX)")
