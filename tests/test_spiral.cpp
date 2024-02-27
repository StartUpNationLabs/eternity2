#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "board/spiral.h"

TEST_CASE("Spiral Order From Board Size", "[spiral]") {
    Spiral spiral;

    SECTION("Board size 2") {
        std::vector<int> expected = {1, 3, -1, 2, -1, 3, 0, 2, 1, 3, 0, -1, 1, -1, 0, 2};
        REQUIRE(spiral.spiral_order_from_board_size(2) == expected);
    }

    SECTION("Board size 3") {
        std::vector<int> expected = {1, 2, 5, 4, -1, 8, 3, 6, 7, 1, 4, 5, 0, -1, 8, 3, 6, 7, 1, 2, 5, 0, -1, 8, 3, 4, 7,
                                     1, 2, 5, 0, -1, 4, 3, 6, 7};
        REQUIRE(spiral.spiral_order_from_board_size(3) == expected);
    }

}