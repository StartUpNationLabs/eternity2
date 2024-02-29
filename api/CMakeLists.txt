cmake_minimum_required(VERSION 3.23)
#
# c++ standard 20
set(CMAKE_CXX_STANDARD 20)
find_package(Protobuf REQUIRED)
find_package(asio-grpc CONFIG REQUIRED)
find_package(Boost REQUIRED COMPONENTS coroutine)
find_package(Threads REQUIRED)
find_package(unifex CONFIG REQUIRED)
# example helper
add_library(asio-grpc-example-helper INTERFACE)

target_include_directories(asio-grpc-example-helper INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/helper")
# example protos
add_subdirectory(proto)

# examples
add_executable(asio-grpc-example)

target_sources(asio-grpc-example PRIVATE main.cpp)
# print found boost
message(STATUS "Boost_INCLUDE_DIRS: ${Boost_INCLUDE_DIRS}")
target_link_libraries(
        asio-grpc-example
        PRIVATE asio-grpc-example-helper
        asio-grpc-example-protos asio-grpc::asio-grpc Boost::coroutine
        Threads::Threads
        asio-grpc::asio-grpc-unifex
        unifex::unifex
)