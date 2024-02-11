#include <iostream>
#include <csv.h>

#include "piece/piece.h"
#include "board/board.h"
#include "spdlog/spdlog.h"
#include "piece_loader/piece_loader.h"

void thread_function(int board_size, std::vector<PIECE> pieces, Board &max_board, int &max_count, std::mutex &mutex) {

    Board board = create_board(board_size);
    auto start = std::chrono::high_resolution_clock::now();
    solve_board(board, pieces, max_board, max_count, mutex);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;
    std::cout << board_size << "x" << board_size << " board solved in " << elapsed.count() << " seconds" << std::endl;
    std::vector<std::string> board_lines = board_to_string(board);
    for (auto const &line: board_lines) {
        std::cout << line << std::endl;
    }
}


int main(int argc, char *argv[]) {
    std::string filename = "file.csv";
    if (argc == 2) {
        filename = argv[1];
    }
    auto pieces = load_from_csv(filename);
    auto board_size = (int) sqrt((int) pieces.size());
    std::mutex mutex;
    Board max_board = create_board(board_size);
//    int max_count = 0;
//    thread_function(board_size, pieces, max_board, max_count, mutex);
    int max_count = 0;
    std::vector<std::jthread> threads;
    for (int i = 0; i < 16; i++) {
        threads.emplace_back(thread_function, board_size, pieces, std::ref(max_board), std::ref(max_count),
                             std::ref(mutex));
    }
    // every 2 seconds, print the current max count
    bool stop = false;
    while (!stop) {
        std::this_thread::sleep_for(std::chrono::seconds(2));
        std::cout << "Max count: " << max_count << std::endl;
        for (std::vector<std::string> board_lines = board_to_string(max_board); auto const &line: board_lines) {
            std::cout << line << std::endl;
        }
        // if board is solved, stop the threads
        if (max_count == board_size * board_size) {
            stop = true;
            exit(0);
        }
    }
    export_board(max_board);
    return 0;
}
