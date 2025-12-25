cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 20)

include(CheckCXXCompilerFlag)

# SIMD detection and configuration
if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm|aarch64|ARM64")
    set(ETERNITY2_SIMD_TYPE "NEON")
    message(STATUS "Target architecture: ARM")
    check_cxx_compiler_flag("-march=armv8-a+simd" HAS_ARM_SIMD)
    if(HAS_ARM_SIMD)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=armv8-a+simd")
        message(STATUS "SIMD: ARM NEON enabled")
    endif()
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    message(STATUS "Target architecture: x86_64")
    check_cxx_compiler_flag("-mavx512f -mavx512bw" HAS_AVX512)
    check_cxx_compiler_flag("-mavx2" HAS_AVX2)

    if(HAS_AVX512)
        set(ETERNITY2_SIMD_TYPE "AVX512")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mavx512f -mavx512bw")
        message(STATUS "SIMD: AVX-512 enabled")
    elseif(HAS_AVX2)
        set(ETERNITY2_SIMD_TYPE "AVX2")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mavx2")
        message(STATUS "SIMD: AVX2 enabled")
    else()
        set(ETERNITY2_SIMD_TYPE "SCALAR")
        message(STATUS "SIMD: Scalar fallback (no SIMD)")
    endif()
else()
    set(ETERNITY2_SIMD_TYPE "SCALAR")
    message(STATUS "SIMD: Scalar fallback (unknown architecture)")
endif()

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
        piece_search/piece_search_optimized.cpp
        piece_search/piece_search_optimized.h
        board/board.cpp
        board/board.h
        format/format.cpp
        format/format.h
        solver/solver.h
        solver/solver.cpp
        board/scan_row.cpp
        board/scan_row.h
        board/spiral.cpp
        board/spiral.h
        hash_load_store/hash_store_load.cpp
        hash_load_store/hash_store_load.h
        board/scan_utils.cpp
        board/scan_utils.h
        simd/simd_detect.h
        simd/simd_ops.h
        simd/simd_ops.cpp
        hash/bloom_filter.h
        hash/bloom_filter.cpp)

target_include_directories(solver_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_compile_definitions(solver_lib PUBLIC DISABLE_LOGGING)
set_target_properties(solver_lib PROPERTIES LINKER_LANGUAGE CXX)

#find_package(OpenMP)
add_executable(Solver main.cpp
)
target_link_libraries(Solver solver_lib)
