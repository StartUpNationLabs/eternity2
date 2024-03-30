#define CONFIG_CATCH_MAIN

#include "board/scan_row.h"
#include "board/spiral.h"

#include <catch2/catch_all.hpp>

TEST_CASE("Row scan order", "[scan_row_order_from_board_size]")
{
    auto scan_row_order = ScanRow::scan_row_order_from_board_size(2);
    REQUIRE(scan_row_order.size() == 4);
    REQUIRE(scan_row_order[0] == 1);
    REQUIRE(scan_row_order[1] == 2);
    REQUIRE(scan_row_order[2] == 3);
    REQUIRE(scan_row_order[3] == END_PATH);
}

TEST_CASE("Row Scan with get index check", "[scan_row_order_from_board_size]")
{
    int board_size         = 40;
    Board board            = create_board(board_size);
    auto scan_row_order    = ScanRow::scan_row_order_from_board_size(board_size);
    board.next_index_cache = scan_row_order;
    Index index            = {0, 0};
    for (int i = 0; i < board_size * board_size; ++i)
    {
        Index index_scan       = get_next_scan_row(board, index);
        Index cache_index_scan = get_next_using_cache(board, index);
        REQUIRE(index_scan.first == cache_index_scan.first);
        REQUIRE(index_scan.second == cache_index_scan.second);
        index = index_scan;
    }
}
