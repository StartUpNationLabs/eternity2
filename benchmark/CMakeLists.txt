cmake_minimum_required(VERSION 3.10)

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

# Benchmark executable
add_executable(benchmark
    benchmark.cpp
    main.cpp
)

# Include directories
target_include_directories(benchmark PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../solver
    ${CMAKE_CURRENT_SOURCE_DIR}/../solver_v2
)

# Link to both solver libraries
target_link_libraries(benchmark
    solver_v2_lib
    solver_lib
)

# Disable logging for performance
target_compile_definitions(benchmark PUBLIC DISABLE_LOGGING)

message(STATUS "Building Eternity II Benchmark Tool")

