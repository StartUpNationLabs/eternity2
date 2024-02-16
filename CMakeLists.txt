cmake_minimum_required(VERSION 3.10)
project(eternity2)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -m64")

# if not apple
if (NOT APPLE)
    enable_testing()
    add_subdirectory(tests)
endif ()
add_subdirectory(solver)
