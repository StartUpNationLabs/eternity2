cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 20)


if (APPLE)
    # set(CMAKE_C_COMPILER gcc-12)
    # set(CMAKE_CXX_COMPILER gcc-12)
endif ()


# add Wall flag
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}") #  -Wall -lstdc++
# build release
set(CMAKE_BUILD_TYPE Release)

# Define the macro
set(SCAN_METHOD "ROW" CACHE STRING "Method to scan the board")

# Add the macro definition to your compiler flags
if (SCAN_METHOD STREQUAL "ROW")
    add_definitions(-DSCAN_METHOD_ROW)

elseif (SCAN_METHOD STREQUAL "SPIRAL")
    add_definitions(-DSCAN_METHOD_SPIRAL)

endif ()

# add library
add_library(solver_lib STATIC
        piece/piece.cpp
        piece/piece.h
        piece_loader/piece_loader.cpp
        piece_loader/piece_loader.h
        piece_search/piece_search.cpp
        piece_search/piece_search.h
        board/board.cpp
        board/board.h
        format/format.cpp
        format/format.h
        solver/solver.h
        solver/solver.cpp board/scan_row.cpp board/scan_row.h board/spiral.cpp board/spiral.h
        hash_load_store/hash_store_load.cpp
        hash_load_store/hash_store_load.h
        board/scan_utils.cpp
        board/scan_utils.h)

target_include_directories(solver_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_compile_definitions(solver_lib PUBLIC DISABLE_LOGGING)
set_target_properties(solver_lib PROPERTIES LINKER_LANGUAGE CXX)

#find_package(OpenMP)
add_executable(Solver main.cpp
)
target_link_libraries(Solver solver_lib)
