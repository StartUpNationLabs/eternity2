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
    }SECTION("Create 3x3 board") {
        Board board = create_board(3);
        REQUIRE(board.size() == 3);
        REQUIRE(board[0].size() == 3);
        REQUIRE(board[1].size() == 3);
        REQUIRE(board[2].size() == 3);
        log_board(board, "3x3 board");
    }SECTION("Create 4x4 board") {
        Board board = create_board(4);
        REQUIRE(board.size() == 4);
        REQUIRE(board[0].size() == 4);
        REQUIRE(board[1].size() == 4);
        REQUIRE(board[2].size() == 4);
        REQUIRE(board[3].size() == 4);
        log_board(board, "4x4 board");
    }
}

TEST_CASE("Board place", "[place]") {
    SECTION("place piece in 2x2 board") {
        Board board = create_board(2);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 0, 0);
        log_board(board, "2x2 board with piece");
        REQUIRE(board[0][0].piece == piece);
        REQUIRE(board[0][0].rotation == 0);
    }SECTION("place piece in 3x3 board") {
        Board board = create_board(3);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 1, 1);
        log_board(board, "3x3 board with piece");
        REQUIRE(board[1][1].piece == piece);
        REQUIRE(board[1][1].rotation == 0);
    }SECTION("place piece in 4x4 board") {
        Board board = create_board(4);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 2, 2);
        log_board(board, "4x4 board with piece");
        REQUIRE(board[2][2].piece == piece);
        REQUIRE(board[2][2].rotation == 0);
    }
}

TEST_CASE("Board remove", "[remove]") {
    SECTION("remove piece in 2x2 board") {
        Board board = create_board(2);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 0, 0);
        log_board(board, "2x2 board with piece");
        remove_piece(board, 0, 0);
        log_board(board, "2x2 board without piece");
        REQUIRE(board[0][0].piece == 0);
        REQUIRE(board[0][0].rotation == 0);
    }SECTION("remove piece in 3x3 board") {
        Board board = create_board(3);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 1, 1);
        log_board(board, "3x3 board with piece");
        remove_piece(board, 1, 1);
        log_board(board, "3x3 board without piece");
        REQUIRE(board[1][1].piece == 0);
        REQUIRE(board[1][1].rotation == 0);
    }SECTION("remove piece in 4x4 board") {
        Board board = create_board(4);
        PIECE piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, 2, 2);
        log_board(board, "4x4 board with piece");
        remove_piece(board, 2, 2);
        log_board(board, "4x4 board without piece");
        REQUIRE(board[2][2].piece == 0);
        REQUIRE(board[2][2].rotation == 0);
    }
}

TEST_CASE("Possible pieces") {
    SECTION("Test possible pieces in 2x2 board") {
        Board board = create_board(2);
        PIECE piece = make_piece(1, 2, WALL, WALL);
        log_board(board, "2x2 board with piece");
        std::vector<RotatedPiece> possible = possible_pieces(board, {piece}, 1, 1);
        REQUIRE(possible.size() == 1);
        REQUIRE(possible[0].piece == piece);
        REQUIRE(possible[0].rotation == 3);
        place_piece(board, possible[0], 1, 1);
        log_board(board, "2x2 board with piece placed");

    }

}


TEST_CASE("Solve Board") {
    SECTION("Solve 2x2 board") {
        Board board = create_board(2);
        std::vector<PIECE> pieces = {
                make_piece(1, 1, WALL, WALL),
                make_piece(1, WALL, WALL, 1),
                make_piece(WALL, WALL, 1, 1),
                make_piece(1, 1, WALL, WALL)
        };
        solve_board(board, pieces);
        log_board(board, "2x2 board solved");
    }

    SECTION("Solve 3x3 board") {
        Board board = create_board(3);
        std::vector<PIECE> pieces = {
                make_piece(1, 1, WALL, WALL),
                make_piece(1, WALL, WALL, 1),
                make_piece(WALL, WALL, 1, 1),
                make_piece(1, 1, WALL, WALL),


                make_piece(1, 1, WALL, 1),
                make_piece(1, WALL, 1, 1),
                make_piece(1, 1, 1, WALL),
                make_piece(WALL, 1, 1, 1),

                make_piece(1, 1, 1, 1),



        };
        solve_board(board, pieces);
        log_board(board, "3x3 board solved");
    }

}

