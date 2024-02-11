#include <iostream>
#include <csv.h>

#include "piece/piece.h"
#include "board/board.h"
#include "spdlog/spdlog.h"
#include "piece_loader/piece_loader.h"


int main(int argc, char *argv[]){
    std::string filename = "file.csv";
    if (argc == 2) {
        filename = argv[1];
    }
    auto pieces = load_from_csv(filename);
    auto board_size = (int) sqrt((int) pieces.size());
    Board board = create_board(board_size);
    auto start = std::chrono::high_resolution_clock::now();
    solve_board(board, pieces);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    std::cout << board_size << "x" << board_size << " board solved in " << elapsed.count() << " seconds" << std::endl;
    std::vector<std::string> board_lines = board_to_string(board);
    for (auto const &line: board_lines) {
        std::cout << line << std::endl;
    }
}
