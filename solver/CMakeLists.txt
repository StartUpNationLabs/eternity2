cmake_minimum_required(VERSION 3.22)
set(CMAKE_CXX_STANDARD 20)
add_executable(Solver main.cpp
        piece/piece.cpp
        piece/piece.h
        piece_loader/piece_loader.cpp
        piece_loader/piece_loader.h
        piece_search/piece_search.cpp
        piece_search/piece_search.h
)
target_link_libraries(Solver spdlog csv)
# add Wall flag
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
# build release
#set(CMAKE_BUILD_TYPE Release)

# add library
add_library(solver_lib STATIC
        piece/piece.cpp
        piece/piece.h
        piece_loader/piece_loader.cpp
        piece_loader/piece_loader.h
        piece_search/piece_search.cpp
        piece_search/piece_search.h)

target_include_directories(solver_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(solver_lib spdlog csv)
set_target_properties(solver_lib PROPERTIES LINKER_LANGUAGE CXX)