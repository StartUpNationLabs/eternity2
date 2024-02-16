cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 17)


if(APPLE)
    set(CMAKE_C_COMPILER clang)
    set(CMAKE_CXX_COMPILER clang++)

    if(CMAKE_C_COMPILER_ID MATCHES "Clang\$")
        set(OpenMP_C_FLAGS "-Xpreprocessor -fopenmp")
        set(OpenMP_C_LIB_NAMES "omp")
        set(OpenMP_omp_LIBRARY omp)
    endif()

    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang\$")
        set(OpenMP_CXX_FLAGS "-Xpreprocessor -fopenmp")
        set(OpenMP_CXX_LIB_NAMES "omp")
        set(OpenMP_omp_LIBRARY omp)
    endif()

endif()


# add Wall flag
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
# build release
set(CMAKE_BUILD_TYPE Release)

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
        format/format.h)

target_include_directories(solver_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_compile_definitions(solver_lib PUBLIC SPDLOG_ACTIVE_LEVEL=SPDLOG_LEVEL_TRACE)
set_target_properties(solver_lib PROPERTIES LINKER_LANGUAGE CXX)

#find_package(OpenMP)
add_executable(Solver main.cpp
)
target_link_libraries(Solver solver_lib)
