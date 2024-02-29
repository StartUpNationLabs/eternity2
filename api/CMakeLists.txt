cmake_minimum_required(VERSION 3.23)
#
find_package(Protobuf REQUIRED)
#find_package(GRPC REQUIRED)
# sa charge sa charge xD
#j'ai mis cmake 3.29
# 3.29? oui
# mais gcc est 11.4, je sais pas si ça va suffire.Pour cpp 20 oui
# peut-être que grpcxx utilise des trucs trop récent, on va voir
#laisse moi essayer
# vasy
FetchContent_Declare(grpcxx
        URL      https://github.com/uatuko/grpcxx/archive/refs/tags/v0.2.0.tar.gz
        URL_HASH SHA256=ed0e0c6ccd44aabb9447de9030b9be092bfb97cb654d69c970cbefd7b7bb44da
)
FetchContent_MakeAvailable(grpcxx)
add_subdirectory(proto)

add_executable(${PROJECT_NAME}-grpc
        main.cpp
)

# add gcc flags -fcoroutines
target_compile_features(${PROJECT_NAME}-grpc PRIVATE cxx_std_20)

target_link_libraries(${PROJECT_NAME}-grpc
        PRIVATE
        helloworld-proto
        libgrpcxx::grpcxx
)