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

# solver_v2 library sources
set(SOLVER_V2_SOURCES
    constraints/domain.cpp
    heuristics/variable_ordering.cpp
    heuristics/value_ordering.cpp
    solver/solver_v2.cpp
)

# solver_v2 library headers
set(SOLVER_V2_HEADERS
    constraints/domain.h
    heuristics/variable_ordering.h
    heuristics/value_ordering.h
    solver/solver_v2.h
)

# Create solver_v2 library (links to solver_lib from v1 for shared types)
add_library(solver_v2_lib STATIC ${SOLVER_V2_SOURCES} ${SOLVER_V2_HEADERS})

# Include directories
target_include_directories(solver_v2_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../solver
)

# Link to v1 solver_lib for shared types (Piece, Board, etc.)
target_link_libraries(solver_v2_lib PUBLIC solver_lib)

# Disable logging in v2 for performance
target_compile_definitions(solver_v2_lib PUBLIC DISABLE_LOGGING)

# Create solver_v2 executable
add_executable(SolverV2 main.cpp)
target_link_libraries(SolverV2 solver_v2_lib)

# Optional: benchmark executable for comparing v1 vs v2
# add_executable(benchmark benchmark.cpp)
# target_link_libraries(benchmark solver_v2_lib solver_lib)

message(STATUS "Building Eternity II Solver v2 with MAC, MRV, LCV optimizations")
