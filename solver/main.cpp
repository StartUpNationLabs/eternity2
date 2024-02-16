#include <iostream>
#include <valarray>
#include <thread>

#include "piece/piece.h"
#include "board/board.h"
#include "piece_loader/piece_loader.h"

void thread_function(int board_size, std::vector<PIECE> pieces, Board &max_board, int &max_count, std::mutex &mutex) {
    Board board = create_board(board_size);
    solve_board(board, pieces, max_board, max_count, mutex);
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
    for (auto const &piece: pieces) {
        std::vector<std::string> piece_lines = piece_to_string(piece);
        for (auto const &line: piece_lines) {
            std::cout << line << std::endl;
        }
    }
    auto board_size = (int) sqrt((int) pieces.size());
    std::mutex mutex;
    Board max_board = create_board(board_size);
    int max_count = 0;
    std::vector<std::thread> threads;
    threads.reserve(16);
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 16; i++) {
        threads.emplace_back(thread_function,
                             board_size,
                             pieces,
                             std::ref(max_board),
                             std::ref(max_count),
                             std::ref(mutex)
                             );
    }
    // every 2 seconds, print the current max count
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(2));
        std::cout << "Max count: " << max_count << std::endl;
        std::vector<std::string> board_lines = board_to_string(max_board);
        for ( auto const &line: board_lines) {
            std::cout << line << std::endl;
        }
        // if board is solved, stop the threads
        if (max_count == board_size * board_size) {
            auto end = std::chrono::high_resolution_clock::now();
           // stop threads
            for (auto &thread: threads) {
                thread.join();
            }
            // export the board
            std::chrono::duration<double> elapsed = end - start;
            std::cout << board_size << "x" << board_size << " board solved in " << elapsed.count() << " seconds" << std::endl;
            export_board(max_board);
            return 0;
        }
    }
}
