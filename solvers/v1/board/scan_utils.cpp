//
// Created by appad on 30/03/2024.
//

#include "scan_utils.h"

#include <algorithm>
bool check_path(const std::vector<int> &custom_path, unsigned long long board_size)
{
    std::vector<int> scan_row_order     = ScanRow::scan_row_order_from_board_size(board_size);
    std::vector<int> sorted_custom_path = custom_path;
    std::sort(sorted_custom_path.begin(), sorted_custom_path.end());
    std::sort(scan_row_order.begin(), scan_row_order.end());
    return scan_row_order == sorted_custom_path;
}
