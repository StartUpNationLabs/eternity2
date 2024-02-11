#include <iostream>
#include <csv.h>

#include "piece/piece.h"
#include "board/board.h"
#include "spdlog/spdlog.h"
#include "piece_loader/piece_loader.h"


int main() {
    auto pieces = load_from_csv("file.csv");
    Board board = create_board(8);
    auto start = std::chrono::high_resolution_clock::now();
    solve_board(board, pieces);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    std::cout << "3x3 board solved in " << elapsed.count() << " seconds" << std::endl;
    std::vector<std::string> board_lines = board_to_string(board);
    for (auto const &line: board_lines) {
        std::cout << line << std::endl;
    }
}
