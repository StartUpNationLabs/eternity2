#include <iostream>
#include <valarray>
#include <thread>

#include "piece/piece.h"
#include "board/board.h"
#include "piece_loader/piece_loader.h"
#include "solver/solver.h"

void thread_function(int board_size, std::vector<Piece> pieces, SharedData &shared_data) {
    Board board = create_board(board_size);
    solve_board(board, pieces, shared_data);
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
    int max_count = 0;
    std::vector<std::thread> threads;
    unsigned long thread_count = 16;
    if (std::thread::hardware_concurrency() != 0) {
        thread_count = std::thread::hardware_concurrency();
    }
    threads.reserve(thread_count);
    std::unordered_set<BoardHash> hashes;
    SharedData shared_data = {max_board, max_count, mutex, hashes};
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < thread_count; i++) {
        threads.emplace_back(thread_function,
                             board_size,
                             pieces,
                             std::ref(shared_data)
        );
    }
    // every 2 seconds, print the current max count
    long long int last_max_count = 0;
    while (true) {
        std::this_thread::sleep_for(std::chrono::nanoseconds(200));
        if (max_count == board_size * board_size) {
            std::cout << "==" << std::endl;
            std::string board_lines = export_board_to_csv_string(max_board);
            std::cout << board_lines;
            auto end = std::chrono::high_resolution_clock::now();
            // export the board
            std::chrono::duration<double> elapsed = end - start;
            std::cout << "=time=" << elapsed.count() << std::endl;
            std::cout << "=" << "Stopping threads" << std::endl;
            // stop threads
            for (auto &thread: threads) {
                thread.join();
            }
            return 0;
        }
        if (last_max_count == max_count) {
            continue;
        }
        last_max_count = max_count;
        std::cout << "==" << std::endl;
        std::string board_lines = export_board_to_csv_string(max_board);
        std::cout << board_lines;
    }
}
