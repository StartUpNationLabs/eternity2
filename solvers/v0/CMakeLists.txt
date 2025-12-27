# V0 Solver Library (Original Simple Backtracking)
add_library(solver_v0_lib
    solver_v0.cpp
    solver_v0.h
)

target_link_libraries(solver_v0_lib
    PUBLIC solver_lib  # Reuse v1's board and piece infrastructure
)

target_include_directories(solver_v0_lib
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..
)
