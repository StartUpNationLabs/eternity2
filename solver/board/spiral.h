//
// Created by Raphaël Anjou on 27/02/2024.
//

#ifndef ETERNITY2_SPIRAL_H
#define ETERNITY2_SPIRAL_H


#include <vector>
#include <cmath>
#include "../board/board.h"
#include "../piece/piece.h"

class Spiral {
public:
    static std::pair<int, int> convert_1d_to_2d(int board_size, int index) {
        return std::make_pair(index / board_size, index % board_size);
    }

    static int convert_2d_to_1d(int board_size, std::pair<int, int> index) {
        return index.first * board_size + index.second;
    }

    static std::vector<int> spiral_order_1d(const std::vector<int> &matrix_1d, int start_index_1d);

    static std::vector<int> spiral_order_from_board_size(int board_size);

    Index get_next(const Board &board, Index index);
};

#endif //ETERNITY2_SPIRAL_H
