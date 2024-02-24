#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "board/board.h"
#include "format/format.h"


TEST_CASE("Board Creation", "[create]"){
    SECTION("Create 4x4 board") {
        Board board = create_board(4);
        REQUIRE(board.board.size() == 4 * 4);
        log_board(board, "4x4 board");
    }
}

TEST_CASE("Board place", "[place]") {
    SECTION("place piece in 2x2 board") {
        Board board = create_board(2);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {0, 0});
        log_board(board, "2x2 board with piece");
        REQUIRE(board.board[get_1d_board_index(board,{0,0})].piece == piece);
        REQUIRE(board.board[get_1d_board_index(board,{0,0})].rotation == 0);
    }SECTION("place piece in 3x3 board") {
        Board board = create_board(3);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {1, 1});
        log_board(board, "3x3 board with piece");
        REQUIRE(board.board[get_1d_board_index(board,{1,1})].piece == piece);
        REQUIRE(board.board[get_1d_board_index(board,{1,1})].rotation == 0);
    }SECTION("place piece in 4x4 board") {
        Board board = create_board(4);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {2, 2});
        log_board(board, "4x4 board with piece");
        REQUIRE(board.board[get_1d_board_index(board,{2,2})].piece == piece);
        REQUIRE(board.board[get_1d_board_index(board,{2,2})].rotation == 0);
    }
}

TEST_CASE("Board remove", "[remove]") {
    SECTION("remove piece in 2x2 board") {
        Board board = create_board(2);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {0, 0});
        log_board(board, "2x2 board with piece");
        remove_piece(board, {0, 0});
        log_board(board, "2x2 board without piece");
        REQUIRE(board.board[get_1d_board_index(board,{0,0})].piece == 0);
        REQUIRE(board.board[get_1d_board_index(board,{0,0})].rotation == 0);
    }SECTION("remove piece in 3x3 board") {
        Board board = create_board(3);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {1, 1});
        log_board(board, "3x3 board with piece");
        remove_piece(board, {1, 1});
        log_board(board, "3x3 board without piece");
        REQUIRE(board.board[get_1d_board_index(board,{1,1})].piece == 0);
        REQUIRE(board.board[get_1d_board_index(board,{1,1})].rotation == 0);
    }SECTION("remove piece in 4x4 board") {
        Board board = create_board(4);
        Piece piece = make_piece(1, 2, 3, 4);
        RotatedPiece rotated_piece = {piece, 0};
        place_piece(board, rotated_piece, {2, 2});
        log_board(board, "4x4 board with piece");
        remove_piece(board, {2, 2});
        log_board(board, "4x4 board without piece");
        REQUIRE(board.board[get_1d_board_index(board,{2,2})].piece == 0);
        REQUIRE(board.board[get_1d_board_index(board,{2,2})].rotation == 0);
    }
}


TEST_CASE("Board get_neighbors", "[neighbors]") {
    SECTION("get neighbors of 2x2 board") {
        Board board = create_board(2);
        place_piece(board, {make_piece(1, 2, 3, 4), 0}, {0, 0});
        place_piece(board, {make_piece(1, 2, 3, 4), 0}, {1, 0});
        place_piece(board, {make_piece(1, 2, 3, 4), 0}, {0, 1});
        place_piece(board, {make_piece(1, 2, 3, 4), 0}, {1, 1});
        log_board(board, "2x2 board with pieces");
        Neighbor neighbors = get_neighbors(board, {0, 0});
        REQUIRE(neighbors.up == nullptr);
        REQUIRE(neighbors.right == &board.board[get_1d_board_index(board,{1,0})]);
        REQUIRE(neighbors.down == &board.board[get_1d_board_index(board,{0,1})]);
        REQUIRE(neighbors.left == nullptr);
        neighbors = get_neighbors(board, {1, 0});
        REQUIRE(neighbors.up == nullptr);
        REQUIRE(neighbors.right == nullptr);
        REQUIRE(neighbors.down == &board.board[get_1d_board_index(board,{1,1})]);
        REQUIRE(neighbors.left == &board.board[get_1d_board_index(board,{0,0})]);
        neighbors = get_neighbors(board, {0, 1});
        REQUIRE(neighbors.up == &board.board[get_1d_board_index(board,{0,0})]);
        REQUIRE(neighbors.right == &board.board[get_1d_board_index(board,{1,1})]);
        REQUIRE(neighbors.down == nullptr);
        REQUIRE(neighbors.left == nullptr);
        neighbors = get_neighbors(board, {1, 1});
        REQUIRE(neighbors.up == &board.board[get_1d_board_index(board,{1,0})]);
        REQUIRE(neighbors.right == nullptr);
        REQUIRE(neighbors.down == nullptr);
        REQUIRE(neighbors.left == &board.board[get_1d_board_index(board,{0,1})]);
    }
}
