//
// Created by Raphaël Anjou on 27/02/2024.
//

#ifndef ETERNITY2_SCAN_ROW_H
#define ETERNITY2_SCAN_ROW_H

#include "board.h"

#include <vector>
class ScanRow
{
public:
    static auto scan_row_order_from_board_size(int board_size) -> std::vector<int>
    {
        std::vector<int> scan_row_order;
        scan_row_order.reserve(board_size * board_size - 1);
        for (int i = 0; i < board_size * board_size - 1; ++i)
        {
            scan_row_order.push_back(i + 1);
        }
        // max integer value
        scan_row_order.push_back(END_PATH);
        return scan_row_order;
    }
};

#endif //ETERNITY2_SCAN_ROW_H
