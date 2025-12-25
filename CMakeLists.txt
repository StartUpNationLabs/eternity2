cmake_minimum_required(VERSION 3.10)
project(eternity2)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")

add_subdirectory(solver)
add_subdirectory(api)

# Tests are optional - only build if Catch2 is available
find_package(Catch2 CONFIG QUIET)
if(Catch2_FOUND)
    message(STATUS "Catch2 found - building tests")
    enable_testing()
    add_subdirectory(tests)
else()
    message(WARNING "Catch2 not found - skipping tests. Install via vcpkg or use -DCMAKE_TOOLCHAIN_FILE")
endif()