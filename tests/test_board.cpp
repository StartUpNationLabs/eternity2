#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "board/board.h"


TEST_CASE("Board Creation", "[create]") {
    SECTION("Create 2x2 board") {
        Board board = create_board(2);
        REQUIRE(board.size() == 2);
        REQUIRE(board[0].size() == 2);
        REQUIRE(board[1].size() == 2);
        log_board(board, "2x2 board");
    }
    SECTION("Create 3x3 board") {
        Board board = create_board(3);
        REQUIRE(board.size() == 3);
        REQUIRE(board[0].size() == 3);
        REQUIRE(board[1].size() == 3);
        REQUIRE(board[2].size() == 3);
        log_board(board, "3x3 board");
    }
    SECTION("Create 4x4 board") {
        Board board = create_board(4);
        REQUIRE(board.size() == 4);
        REQUIRE(board[0].size() == 4);
        REQUIRE(board[1].size() == 4);
        REQUIRE(board[2].size() == 4);
        REQUIRE(board[3].size() == 4);
        log_board(board, "4x4 board");
    }
}

