Include(FetchContent)

FetchContent_Declare(
        Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG        v3.5.0 # or a later release
)

FetchContent_MakeAvailable(Catch2)

add_executable(tests
        test_piece.cpp
        test_piece_search.cpp
        test_board.cpp
        test_piece_load.cpp
        test_solve_board.cpp
)
target_link_libraries(tests Catch2::Catch2WithMain solver_lib)
include(CTest)
include(Catch)
catch_discover_tests(tests)
