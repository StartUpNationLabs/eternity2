find_package(Catch2 CONFIG REQUIRED)


add_executable(tests
        test_piece.cpp
        test_piece_search.cpp
        test_query_semantics.cpp
        test_board.cpp
        test_piece_load.cpp
        test_solve_board.cpp
        test_spiral.cpp
        test_scan_row.cpp
        test_solver_v2.cpp)
target_link_libraries(tests Catch2::Catch2WithMain solver_lib solver_v2_lib)
include(CTest)
include(Catch)
catch_discover_tests(tests)
