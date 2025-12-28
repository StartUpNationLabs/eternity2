//
// Eternity II Solver v2 - Main Entry Point
// Optimized solver with MAC, MRV, LCV heuristics
//

#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>
#include <stdexcept>

#include "common/types.h"
#include "common/piece_utils.h"
#include "common/piece_loader.h"
#include "v1/board/board.h"
#include "common/utils.h"
#include "common/arg_parser.h"
#include "common/logger.h"
#include "solver/solver_v2.h"
#include "parallel/parallel_solver.h"

/**
 * @brief Execute the solver with the given configuration
 *
 * @param config Solver configuration
 * @param board_pieces Board and pieces to solve
 * @param board_size Size of the board
 * @param partition_depth Partition depth for parallel mode
 * @param quiet Whether to suppress output
 * @param print_stats Whether to print statistics
 * @param puzzle_name Name of the puzzle for BUCAS URL generation
 * @return SolveResult The result of the solving process
 */
eternity2_v2::SolveResult execute_solver(const eternity2_v2::SolverConfig& config,
                                         const std::pair<Board, std::vector<Piece>>& board_pieces,
                                         size_t board_size,
                                         size_t partition_depth,
                                         bool quiet,
                                         bool print_stats,
                                         const std::string& puzzle_name = "puzzle") {
    // Setup solver
    std::mutex mutex;
    Board max_board = create_board(static_cast<int>(board_size));

    eternity2_v2::SharedDataV2 shared_data = {
        max_board,
        {0},
        mutex
    };
    shared_data.config = config;
    shared_data.puzzle_name = puzzle_name;

    // Progress callback
    auto progress_start = std::chrono::high_resolution_clock::now();
    if (config.verbose) {
        shared_data.on_board_update = [&, progress_start](const Board& board) {
            static long long last_count = -1;
            if (shared_data.max_count.load() > last_count) {
                last_count = shared_data.max_count.load();
                auto now = std::chrono::high_resolution_clock::now();
                auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - progress_start).count();
                eternity2_logger::info("[{}ms] Progress: {}/{} pieces placed", elapsed_ms, last_count, board_size * board_size);
            }
        };
    }

    // Start timer
    auto start = std::chrono::high_resolution_clock::now();

    // Solve - use parallel solver if enabled
    eternity2_v2::SolveResult result;
    if (config.parallel_enabled && config.num_threads > 1) {
        eternity2_v2::ParallelSolverV2 parallel_solver(board_pieces.second, board_size, shared_data);
        if (partition_depth > 0) {
            parallel_solver.set_partition_depth(partition_depth);
        }
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
            eternity2_logger::info("=== SOLUTION FOUND ===");
        }
        std::cout << "==" << std::endl;
        std::cout << export_board_to_csv_string(shared_data.max_board, puzzle_name);
        std::cout << "=time=" << elapsed.count() << std::endl;
    } else {
        if (!quiet) {
            eternity2_logger::info("Result: {}", eternity2_v2::solve_result_to_string(result));
            eternity2_logger::info("Best: {}/{} pieces", shared_data.max_count.load(), board_size * board_size);
        }
    }

    // Print statistics
    if (print_stats && !quiet) {
        const auto& stats = shared_data.stats;
        eternity2_logger::info("=== Statistics ===");
        eternity2_logger::info("Nodes explored: {}", stats.nodes_explored.load());
        eternity2_logger::info("Backtracks: {}", stats.backtracks.load());
        eternity2_logger::info("Domain wipeouts: {}", stats.domain_wipeouts.load());
        eternity2_logger::info("Max depth: {}", stats.max_depth.load());
        eternity2_logger::info("Time: {} seconds", elapsed.count());

        // Performance metrics
        if (elapsed.count() > 0) {
            double nodes_per_sec = static_cast<double>(stats.nodes_explored.load()) / elapsed.count();
            eternity2_logger::info("Performance: {} nodes/sec", static_cast<size_t>(nodes_per_sec));
        }
    }

    return result;
}

int main(int argc, char* argv[]) {
    // Parse arguments
    eternity2_v2::SolverConfig config;
    bool print_stats = true;
    bool quiet = false;
    size_t partition_depth = 0;
    std::string filename;

    try {
        if (!eternity2_arg_parser::parse_v2_arguments(argc, argv, config, filename, 
                                                       print_stats, quiet, partition_depth)) {
            return 0;  // Help was requested
        }
    } catch (const std::exception& e) {
        eternity2_logger::error("{}", e.what());
        eternity2_arg_parser::print_v2_usage(argv[0]);
        return 1;
    }

    // Load puzzle
    if (!quiet) {
        eternity2_logger::info("Loading puzzle from: {}", filename);
    }

    std::pair<Board, std::vector<Piece>> board_pieces;
    try {
        board_pieces = load_from_csv(filename);
    } catch (const std::exception& e) {
        eternity2_logger::error("Error loading puzzle file: {}", e.what());
        return 1;
    }
    auto board_size = board_pieces.first.size;

    // Set num_threads to hardware concurrency if auto-detect (0)
    if (config.parallel_enabled && config.num_threads == 0) {
        config.num_threads = std::thread::hardware_concurrency();
        if (config.num_threads == 0) {
            config.num_threads = 4;  // Fallback
        }
    }

    if (!quiet) {
        eternity2_logger::info("Puzzle size: {}x{}", board_size, board_size);
        eternity2_logger::info("Pieces: {}", board_pieces.second.size());
        eternity2_logger::info("Configuration:");
        eternity2_logger::info("  MRV: {}", config.use_mrv ? "enabled" : "disabled");
        eternity2_logger::info("  Degree: {}", config.use_degree ? "enabled" : "disabled");
        eternity2_logger::info("  LCV: {}", config.use_lcv ? "enabled" : "disabled");
        if (config.parallel_enabled) {
            eternity2_logger::info("  Parallel: enabled ({} threads)", config.num_threads);
        } else {
            eternity2_logger::info("  Parallel: disabled (single-threaded)");
        }
        if (config.max_time_ms > 0) {
            eternity2_logger::info("  Timeout: {} ms", config.max_time_ms);
        }
        if (config.export_partial) {
            eternity2_logger::info("  Partial export: enabled");
            eternity2_logger::info("    Export dir: {}", config.export_dir);
            eternity2_logger::info("    Export prefix: {}", config.export_prefix);
        }
        eternity2_logger::info("Solving...");
    }

    // Extract puzzle name for BUCAS URL generation
    std::string puzzle_name = extract_puzzle_name(filename);

    // Execute solver
    auto result = execute_solver(config, board_pieces, board_size, partition_depth, quiet, print_stats, puzzle_name);

    return (result == eternity2_v2::SolveResult::SOLVED) ? 0 : 1;
}
