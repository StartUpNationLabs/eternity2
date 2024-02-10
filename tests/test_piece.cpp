#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"

TEST_CASE("PIECE Rotation", "[left][right]") {
    SECTION("Rotate left") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE rotated_piece = rotate_piece_left(piece, 1);
        PIECE piece2 = make_piece(2, 3, 4, 1);
        REQUIRE(rotated_piece == piece2);
    }SECTION("Rotate right") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE rotated_piece = rotate_piece_right(piece, 1);
        PIECE piece2 = make_piece(4, 1, 2, 3);
        REQUIRE(rotated_piece == piece2);
    }
}

TEST_CASE("PIECE Mask", "[mask]") {
    SECTION("Get mask") {
        PIECE mask = get_mask(0);
        REQUIRE(mask == UP_MASK);
    }

    SECTION("Test UP_MASK") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE piece2 = make_piece(1, 0, 0, 0);
        PIECE mask = get_mask(0);
        PIECE piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test RIGHT_MASK") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE piece2 = make_piece(0, 2, 0, 0);
        PIECE mask = get_mask(1);
        PIECE piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test DOWN_MASK") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE piece2 = make_piece(0, 0, 3, 0);
        PIECE mask = get_mask(2);
        PIECE piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }

    SECTION("Test LEFT_MASK") {
        PIECE piece = make_piece(1, 2, 3, 4);
        PIECE piece2 = make_piece(0, 0, 0, 4);
        PIECE mask = get_mask(3);
        PIECE piece_masked = piece & mask;
        REQUIRE(piece_masked == piece2);
    }
}