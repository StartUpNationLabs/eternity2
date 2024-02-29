cmake_minimum_required(VERSION 3.10)
project(eternity2)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -m64")

enable_testing()
add_subdirectory(tests)
add_subdirectory(solver)
add_subdirectory(api)