cmake_minimum_required(VERSION 3.23)

find_package(Protobuf REQUIRED)
find_package(GRPC REQUIRED)

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

# jsp pk cmake refait un full rescan a chaque fois
# oui, c'est bizare
# peut-être parce que t'as le générateur codeblock, jsp ce que c;est
# cmake a plein de générateurs : make, jmake, ninja... et ils ont des niveaux de support différents
# faudrait utiliser ninja idéalement
# si t'arrive a le faire marcher ici xD
#language= je oeux essayer mais faut que tu le mettes dans les settigs clion
# dit ce que je dois faire
# je regarde c'est a ninja
# il y a nija dans le path. Essaie de changer le ninja utilisé par clion. comment tu lance ninja normalement de cmd?
# oui, dans le terminal
# j'ai ninja la ducop?  oui
# bon, tant pis, mets make
# c'est au même endroit dans les settings
# sa lamce
# sa telecharge internet
target_link_libraries(${PROJECT_NAME}-grpc
        PRIVATE
        helloworld-proto
        libgrpcxx::grpcxx
)