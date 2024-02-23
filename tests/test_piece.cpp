#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"

TEST_CASE("Piece Rotation", "[left][right]") {
    SECTION("Rotate left") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece rotated_piece = rotate_piece_left(piece, 1);
        Piece piece2 = make_piece(2, 3, 4, 1);
        REQUIRE(rotated_piece == piece2);
    }SECTION("Rotate right") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece rotated_piece = rotate_piece_right(piece, 1);
        Piece piece2 = make_piece(4, 1, 2, 3);
        REQUIRE(rotated_piece == piece2);
    }
}

TEST_CASE("Piece Mask", "[mask]") {

    SECTION("Test UP_MASK") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece piece2 = make_piece(1, 0, 0, 0);
        Piece mask = UP_MASK;
        Piece piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test RIGHT_MASK") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece piece2 = make_piece(0, 2, 0, 0);
        Piece mask = RIGHT_MASK;
        Piece piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test DOWN_MASK") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece piece2 = make_piece(0, 0, 3, 0);
        Piece mask = DOWN_MASK;
        Piece piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test LEFT_MASK") {
        Piece piece = make_piece(1, 2, 3, 4);
        Piece piece2 = make_piece(0, 0, 0, 4);
        Piece mask = LEFT_MASK;
        Piece piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }
}

TEST_CASE("Piece Part", "[part]") {
    SECTION("Test UP_PART") {
        Piece piece = make_piece(1, 2, 3, 4);
        PiecePart part = get_piece_part(piece, UP_MASK);
        REQUIRE(part == 1);
    }

    SECTION("Test RIGHT_PART") {
        Piece piece = make_piece(1, 2, 3, 4);
        PiecePart part = get_piece_part(piece, RIGHT_MASK);
        REQUIRE(part == 2);
    }

    SECTION("Test DOWN_PART") {
        Piece piece = make_piece(1, 2, 3, 4);
        PiecePart part = get_piece_part(piece, DOWN_MASK);
        REQUIRE(part == 3);
    }

    SECTION("Test LEFT_PART") {
        Piece piece = make_piece(1, 2, 3, 4);
        PiecePart part = get_piece_part(piece, LEFT_MASK);
        REQUIRE(part == 4);
    }
}