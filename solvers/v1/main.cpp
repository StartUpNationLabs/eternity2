#include <iostream>
#include <valarray>
#include <thread>
#include <atomic>
#include <chrono>

#include "common/types.h"
#include "common/piece_utils.h"
#include "board/board.h"
#include "common/piece_loader.h"
#include "solver/solver.h"
#include "common/constants.h"
#include "common/logger.h"

void thread_function(Board board, std::vector<Piece> pieces, SharedData &shared_data) {
    solve_board(board, pieces, shared_data);
}


int main(int argc, char *argv[]) {
    std::string filename = "file.csv";
    if (argc == 2) {
        filename = argv[1];
    }
    
    try {
        auto board_pieces = load_from_csv(filename);
        auto board_size = board_pieces.first.size;
        std::mutex mutex;
        Board max_board = create_board(board_size);
        std::vector<std::thread> threads;
        unsigned long thread_count = eternity2_constants::DEFAULT_THREAD_COUNT;
        if (std::thread::hardware_concurrency() != 0) {
            thread_count = std::thread::hardware_concurrency();
        }
        threads.reserve(thread_count);
        std::unordered_set<BoardHash> hashes;
        long long max_count = 0;
        SharedData shared_data = {max_board, max_count, mutex, hashes};
        auto start = std::chrono::high_resolution_clock::now();
        
        for (int i = 0; i < thread_count; i++) {
            threads.emplace_back(thread_function,
                                 board_pieces.first,
                                 board_pieces.second,
                                 std::ref(shared_data)
            );
        }
        
        // every 200 nanoseconds, print the current max count
        long long int last_max_count = 0;
        const long long target_count = board_size * board_size;
        
        while (!shared_data.stop.load()) {
            std::this_thread::sleep_for(eternity2_constants::PROGRESS_CHECK_INTERVAL_NS);
            long long current_max_count = shared_data.max_count.load();
            
            if (current_max_count == target_count) {
                eternity2_logger::info("Solution found!");
                std::cout << "==" << std::endl;
                std::string board_lines = export_board_to_csv_string(shared_data.max_board);
                std::cout << board_lines;
                auto end = std::chrono::high_resolution_clock::now();
                std::chrono::duration<double> elapsed = end - start;
                std::cout << "=time=" << elapsed.count() << std::endl;
                eternity2_logger::info("Stopping threads");
                std::cout << "=" << "Stopping threads" << std::endl;
                
                // Signal threads to stop
                shared_data.stop = true;
                
                // Wait for all threads to finish
                for (auto &thread: threads) {
                    if (thread.joinable()) {
                        thread.join();
                    }
                }
                return 0;
            }
            
            if (last_max_count != current_max_count) {
                last_max_count = current_max_count;
                std::cout << "==" << std::endl;
                std::string board_lines = export_board_to_csv_string(shared_data.max_board);
                std::cout << board_lines;
            }
        }
        
        // Cleanup: join all threads if we exit the loop for any reason
        shared_data.stop = true;
        for (auto &thread: threads) {
            if (thread.joinable()) {
                thread.join();
            }
        }
        
        return 0;
    } catch (const std::exception& e) {
        eternity2_logger::error("Error: {}", e.what());
        return 1;
    }
}

