cmake_minimum_required(VERSION 3.10)
project(eternity2_solver_v2)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
endif()

# Find Threads package for parallel solver
find_package(Threads REQUIRED)

# solver_v2 library sources
set(SOLVER_V2_SOURCES
    constraints/domain.cpp
    heuristics/variable_ordering.cpp
    heuristics/value_ordering.cpp
    solver/solver_v2.cpp
    parallel/parallel_solver.cpp
)

# solver_v2 library headers
set(SOLVER_V2_HEADERS
    constraints/domain.h
    heuristics/variable_ordering.h
    heuristics/value_ordering.h
    solver/solver_v2.h
    parallel/parallel_solver.h
)

# Create solver_v2 library (links to solver_lib from v1 for shared types)
add_library(solver_v2_lib STATIC ${SOLVER_V2_SOURCES} ${SOLVER_V2_HEADERS})

# Include directories
target_include_directories(solver_v2_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/..  # Add solvers/ to include path so we can use "common/types.h" and "v1/board.h"
)

# Link to v1 solver_lib for shared types (Piece, Board, etc.)
# Also link Threads for parallel solver
target_link_libraries(solver_v2_lib PUBLIC solver_lib Threads::Threads)

# Disable logging in v2 library for performance (PRIVATE so executable can still log)
target_compile_definitions(solver_v2_lib PRIVATE DISABLE_LOGGING)

# Common utilities
set(COMMON_SOURCES
    ../common/arg_parser.cpp
    ../common/piece_utils.cpp
    ../common/piece_loader.cpp
)

# Create solver_v2 executable
add_executable(SolverV2 main.cpp ${COMMON_SOURCES})
target_include_directories(SolverV2 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/..)  # Add solvers/ to include path
target_link_libraries(SolverV2 solver_v2_lib)
# Explicitly enable logging for the executable (remove DISABLE_LOGGING that propagates from solver_lib)
# Use compile option to undefine the macro
target_compile_options(SolverV2 PRIVATE -UDISABLE_LOGGING)

# Optional: benchmark executable for comparing v1 vs v2
# add_executable(benchmark benchmark.cpp)
# target_link_libraries(benchmark solver_v2_lib solver_lib)

message(STATUS "Building Eternity II Solver v2 with MAC, MRV, LCV optimizations")
