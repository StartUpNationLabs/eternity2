//
// Created by Raphaël Anjou on 27/02/2024.
//

#include "spiral.h"


std::vector<int>
Spiral::spiral_order_1d(const std::vector<int> &matrix_1d, int start_index_1d) {
    int side_length = static_cast<int>(std::sqrt(matrix_1d.size()));
    std::pair<int, int> start_index = convert_1d_to_2d(side_length, start_index_1d);
    std::vector<std::vector<bool>> visited(side_length, std::vector<bool>(side_length, false));
    std::vector<int> row_direction = {0, 1, 0, -1};
    std::vector<int> col_direction = {1, 0, -1, 0};
    int current_row = start_index.first;
    int current_col = start_index.second;
    int direction_index = 0;

    if (start_index == std::make_pair(0, side_length - 1)) {
        direction_index = 1;
    } else if (start_index == std::make_pair(side_length - 1, 0)) {
        direction_index = 3;
    } else if (start_index == std::make_pair(side_length - 1, side_length - 1)) {
        direction_index = 2;
    }

    std::vector<int> next_indices_1d(matrix_1d.size(), -1);
    int last_index_1d = -1;
    for (int i = 0; i < side_length * side_length; ++i) {
        int curr_index_1d = convert_2d_to_1d(side_length, {current_row, current_col});
        if (last_index_1d != -1) {
            next_indices_1d[last_index_1d] = curr_index_1d;
        }
        last_index_1d = curr_index_1d;

        visited[current_row][current_col] = true;
        int next_row = current_row + row_direction[direction_index];
        int next_col = current_col + col_direction[direction_index];
        if (next_row >= 0 && next_row < side_length && next_col >= 0 && next_col < side_length &&
            !visited[next_row][next_col]) {
            current_row = next_row;
            current_col = next_col;
        } else {
            direction_index = (direction_index + 1) % 4;
            current_row += row_direction[direction_index];
            current_col += col_direction[direction_index];
        }
    }

    return next_indices_1d;
}

std::vector<int> Spiral::spiral_order_from_board_size(int board_size) {
    std::vector<int> matrix_1d(board_size * board_size);
    for (int i = 0; i < board_size * board_size; ++i) {
        matrix_1d[i] = i;
    }

    std::vector<std::pair<int, int>> corners = {
            {0,              0},
            {0,              board_size - 1},
            {board_size - 1, 0},
            {board_size - 1, board_size - 1}
    };

    std::vector<int> combined_next_indices;
    for (const auto &corner: corners) {
        int start_index_1d = convert_2d_to_1d(board_size, corner);
        std::vector<int> next_indices_1d = spiral_order_1d(matrix_1d, start_index_1d);
        combined_next_indices.insert(combined_next_indices.end(), next_indices_1d.begin(), next_indices_1d.end());
    }

    return combined_next_indices;
}
