//
// Eternity II Solver v2 - Main Entry Point
// Optimized solver with MAC, MRV, LCV heuristics
//

#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>

#include "../solver/piece/piece.h"
#include "../solver/board/board.h"
#include "../solver/piece_loader/piece_loader.h"
#include "solver/solver_v2.h"
#include "parallel/parallel_solver.h"

void print_usage(const char* program_name) {
    std::cout << "Eternity II Solver v2 - Optimized with MAC, MRV, LCV\n\n";
    std::cout << "Usage: " << program_name << " [options] <puzzle_file.csv>\n\n";
    std::cout << "Options:\n";
    std::cout << "  --no-mrv        Disable MRV variable ordering\n";
    std::cout << "  --no-degree     Disable degree heuristic (MRV tie-breaker)\n";
    std::cout << "  --no-lcv        Disable LCV value ordering\n";
    std::cout << "  --random        Use random value ordering (disables LCV)\n";
    std::cout << "  --verbose       Print detailed progress\n";
    std::cout << "  --quiet         Minimal output\n";
    std::cout << "  --stats         Print statistics at end\n";
    std::cout << "  --timeout <ms>  Set timeout in milliseconds\n";
    std::cout << "  --parallel      Enable parallel search mode\n";
    std::cout << "  --threads <n>   Set number of worker threads (default: auto-detect)\n";
    std::cout << "  --help          Show this help message\n";
    std::cout << "\nExamples:\n";
    std::cout << "  " << program_name << " puzzle.csv              # Solve with all optimizations\n";
    std::cout << "  " << program_name << " --no-lcv puzzle.csv     # Disable LCV only\n";
    std::cout << "  " << program_name << " --verbose puzzle.csv    # Verbose output\n";
    std::cout << "  " << program_name << " --parallel puzzle.csv   # Use all CPU cores\n";
    std::cout << "  " << program_name << " --threads 4 puzzle.csv  # Use 4 threads\n";
}

int main(int argc, char* argv[]) {
    // Parse arguments
    eternity2_v2::SolverConfig config;
    config.verbose = false;
    bool print_stats = true;
    bool quiet = false;
    std::string filename;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "--no-mrv") {
            config.use_mrv = false;
        } else if (arg == "--no-degree") {
            config.use_degree = false;
        } else if (arg == "--no-lcv") {
            config.use_lcv = false;
        } else if (arg == "--random") {
            config.use_lcv = false;
        } else if (arg == "--verbose" || arg == "-v") {
            config.verbose = true;
        } else if (arg == "--quiet" || arg == "-q") {
            quiet = true;
            config.verbose = false;
        } else if (arg == "--stats") {
            print_stats = true;
        } else if (arg == "--timeout" && i + 1 < argc) {
            config.max_time_ms = std::stoul(argv[++i]);
        } else if (arg == "--parallel") {
            config.parallel_enabled = true;
            if (config.num_threads <= 1) {
                config.num_threads = 0;  // 0 = auto-detect in ParallelSolverV2
            }
        } else if (arg == "--threads" && i + 1 < argc) {
            config.num_threads = std::stoul(argv[++i]);
            if (config.num_threads > 1) {
                config.parallel_enabled = true;
            }
        } else if (arg[0] != '-') {
            filename = arg;
        } else {
            std::cerr << "Unknown option: " << arg << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }

    if (filename.empty()) {
        std::cerr << "Error: No puzzle file specified\n\n";
        print_usage(argv[0]);
        return 1;
    }

    // Load puzzle
    if (!quiet) {
        std::cout << "Loading puzzle from: " << filename << std::endl;
    }

    auto board_pieces = load_from_csv(filename);
    auto board_size = board_pieces.first.size;

    // Set num_threads to hardware concurrency if auto-detect (0)
    if (config.parallel_enabled && config.num_threads == 0) {
        config.num_threads = std::thread::hardware_concurrency();
        if (config.num_threads == 0) {
            config.num_threads = 4;  // Fallback
        }
    }

    if (!quiet) {
        std::cout << "Puzzle size: " << board_size << "x" << board_size << std::endl;
        std::cout << "Pieces: " << board_pieces.second.size() << std::endl;
        std::cout << "\nConfiguration:\n";
        std::cout << "  MRV: " << (config.use_mrv ? "enabled" : "disabled") << std::endl;
        std::cout << "  Degree: " << (config.use_degree ? "enabled" : "disabled") << std::endl;
        std::cout << "  LCV: " << (config.use_lcv ? "enabled" : "disabled") << std::endl;
        if (config.parallel_enabled) {
            std::cout << "  Parallel: enabled (" << config.num_threads << " threads)" << std::endl;
        } else {
            std::cout << "  Parallel: disabled (single-threaded)" << std::endl;
        }
        if (config.max_time_ms > 0) {
            std::cout << "  Timeout: " << config.max_time_ms << " ms\n";
        }
        std::cout << "\nSolving..." << std::endl;
    }

    // Setup solver
    std::mutex mutex;
    Board max_board = create_board(static_cast<int>(board_size));

    eternity2_v2::SharedDataV2 shared_data = {
        max_board,
        {0},
        mutex
    };
    shared_data.config = config;

    // Progress callback
    if (config.verbose) {
        shared_data.on_board_update = [&](const Board& board) {
            static long long last_count = -1;
            if (shared_data.max_count > last_count) {
                last_count = shared_data.max_count.load();
                std::cout << "Progress: " << last_count << "/" << (board_size * board_size)
                          << " pieces placed" << std::endl;
            }
        };
    }

    // Start timer
    auto start = std::chrono::high_resolution_clock::now();

    // Solve - use parallel solver if enabled
    eternity2_v2::SolveResult result;
    if (config.parallel_enabled && config.num_threads > 1) {
        eternity2_v2::ParallelSolverV2 parallel_solver(board_pieces.second, board_size, shared_data);
        result = parallel_solver.solve();
    } else {
        eternity2_v2::SolverV2 solver(board_pieces.second, board_size, shared_data);
        result = solver.solve();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    // Output result
    if (result == eternity2_v2::SolveResult::SOLVED) {
        if (!quiet) {
            std::cout << "\n=== SOLUTION FOUND ===" << std::endl;
        }
        std::cout << "==" << std::endl;
        std::cout << export_board_to_csv_string(shared_data.max_board);
        std::cout << "=time=" << elapsed.count() << std::endl;
    } else {
        if (!quiet) {
            std::cout << "\nResult: " << eternity2_v2::solve_result_to_string(result) << std::endl;
            std::cout << "Best: " << shared_data.max_count << "/" << (board_size * board_size)
                      << " pieces" << std::endl;
        }
    }

    // Print statistics
    if (print_stats && !quiet) {
        const auto& stats = shared_data.stats;
        std::cout << "\n=== Statistics ===" << std::endl;
        std::cout << "Nodes explored: " << stats.nodes_explored << std::endl;
        std::cout << "Backtracks: " << stats.backtracks << std::endl;
        std::cout << "Domain wipeouts: " << stats.domain_wipeouts << std::endl;
        std::cout << "Max depth: " << stats.max_depth << std::endl;
        std::cout << "Time: " << elapsed.count() << " seconds" << std::endl;

        // Performance metrics
        if (elapsed.count() > 0) {
            double nodes_per_sec = static_cast<double>(stats.nodes_explored) / elapsed.count();
            std::cout << "Performance: " << static_cast<size_t>(nodes_per_sec) << " nodes/sec" << std::endl;
        }
    }

    return (result == eternity2_v2::SolveResult::SOLVED) ? 0 : 1;
}
