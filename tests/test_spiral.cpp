#define CONFIG_CATCH_MAIN

#include "board/scan_row.h"
#include "board/scan_utils.h"
#include "board/spiral.h"

#include <catch2/catch_all.hpp>

#include <random>

TEST_CASE("Spiral Order From Board Size", "[spiral]")
{
    Spiral spiral;

    SECTION("Board size 2")
    {
        std::vector<int> expected = {1, 3, END_PATH, 2};
        REQUIRE(spiral.spiral_order_from_board_size(2) == expected);
    }

    SECTION("Board size 3")
    {
        std::vector<int> expected = {1, 2, 5, 4, END_PATH, 8, 3, 6, 7};
        REQUIRE(spiral.spiral_order_from_board_size(3) == expected);
    }
}

TEST_CASE("Test Same elements with Row", "[spiral]")
{
    int board_size      = 5;
    Board board         = create_board(board_size);
    auto scan_row_order = ScanRow::scan_row_order_from_board_size(board_size);
    auto spiral_order   = Spiral::spiral_order_from_board_size(board_size);

    // sort both vectors
    std::sort(scan_row_order.begin(), scan_row_order.end());
    std::sort(spiral_order.begin(), spiral_order.end());

    REQUIRE(scan_row_order == spiral_order);
}

TEST_CASE("Check Paths", "[spiral]")
{
    int board_size      = 5;
    Board board         = create_board(board_size);
    auto scan_row_order = ScanRow::scan_row_order_from_board_size(board_size);
    auto spiral_order   = Spiral::spiral_order_from_board_size(board_size);

    REQUIRE(check_path(spiral_order, board_size));
}

TEST_CASE("Check Paths random", "[random]")
{
    int board_size      = 5;
    Board board         = create_board(board_size);
    auto scan_row_order = ScanRow::scan_row_order_from_board_size(board_size);
    auto random_order   = scan_row_order;
    auto random         = std::default_random_engine{};
    std::shuffle(random_order.begin(), random_order.end(), random);
    REQUIRE(check_path(random_order, board_size));
}