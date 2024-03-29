cmake_minimum_required(VERSION 3.22)
#
# c++ standard 20
set(CMAKE_CXX_STANDARD 20)
find_package(Protobuf REQUIRED)
find_package(asio-grpc CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(unifex CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
# example helper
add_library(asio-grpc-helper INTERFACE)

target_include_directories(asio-grpc-helper INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/helper")
# example protos
add_subdirectory(proto)

# examples
add_executable(asio-grpc-server

)

target_sources(asio-grpc-server PRIVATE main.cpp
        solver/solvera.cpp
        solver/solvera.h
)
# print found boost
message(STATUS "Boost_INCLUDE_DIRS: ${Boost_INCLUDE_DIRS}")
target_link_libraries(
        asio-grpc-server
        PRIVATE asio-grpc-helper
        asio-grpc-protos
        Threads::Threads
        asio-grpc::asio-grpc-unifex
        unifex::unifex
        solver_lib
        spdlog::spdlog
)

# set release
set(CMAKE_BUILD_TYPE Release)