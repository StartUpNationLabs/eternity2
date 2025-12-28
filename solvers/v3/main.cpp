//
// Eternity II Solver v3 - Main Entry Point
// Dancing Links (DLX) solver with edge propagation
//

#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <fstream>
#include <sstream>

#include "common/types.h"
#include "common/piece_utils.h"
#include "common/piece_loader.h"
#include "common/utils.h"
#include "common/logger.h"
#include "v1/board/board.h"
#include "config/solver_config.h"
#include "solver/dlx_solver.h"
#include "parallel/parallel_dlx_solver.h"

using namespace eternity2_v3;
using namespace eternity2_common;

/**
 * @brief Print usage information for solver v3
 */
void print_v3_usage(const char* program_name) {
    std::cout << "Eternity II Solver v3 - Dancing Links (DLX)\n\n";
    std::cout << "Usage: " << program_name << " [options] <puzzle_file.csv>\n\n";
    std::cout << "Options:\n";
    std::cout << "  --no-s-heuristic     Disable S-heuristic (column selection by min size)\n";
    std::cout << "  --no-edge-propagation  Disable edge compatibility checking\n";
    std::cout << "  --verbose, -v        Print detailed progress\n";
    std::cout << "  --quiet, -q          Minimal output\n";
    std::cout << "  --stats              Print statistics at end (default: on)\n";
    std::cout << "  --timeout <ms>       Set timeout in milliseconds\n";
    std::cout << "  --parallel           Enable parallel search mode\n";
    std::cout << "  --threads <n>        Set number of worker threads (default: auto-detect)\n";
    std::cout << "  --partition-depth <n>  Set partition depth for parallel mode\n";
    std::cout << "  --export-partial     Enable exporting partial solutions\n";
    std::cout << "  --export-dir <dir>   Directory for partial exports (default: .)\n";
    std::cout << "  --export-prefix <p>  Prefix for export filenames\n";
    std::cout << "  --help, -h           Show this help message\n";
    std::cout << "\nExamples:\n";
    std::cout << "  " << program_name << " puzzle.csv               # Solve with DLX\n";
    std::cout << "  " << program_name << " --verbose puzzle.csv     # Verbose output\n";
    std::cout << "  " << program_name << " --parallel puzzle.csv    # Use all CPU cores\n";
    std::cout << "  " << program_name << " --threads 4 puzzle.csv   # Use 4 threads\n";
}

/**
 * @brief Parse command line arguments for v3 solver
 */
bool parse_v3_arguments(int argc, char* argv[],
                        SolverConfig& config,
                        std::string& filename,
                        bool& print_stats,
                        bool& quiet,
                        size_t& partition_depth) {
    // Initialize defaults
    config = SolverConfig{};
    print_stats = true;
    quiet = false;
    partition_depth = 0;
    filename.clear();

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_v3_usage(argv[0]);
            return false;
        } else if (arg == "--no-s-heuristic") {
            config.use_s_heuristic = false;
        } else if (arg == "--no-edge-propagation") {
            config.use_edge_propagation = false;
        } else if (arg == "--verbose" || arg == "-v") {
            config.verbose = true;
        } else if (arg == "--quiet" || arg == "-q") {
            quiet = true;
            config.verbose = false;
        } else if (arg == "--stats") {
            print_stats = true;
        } else if (arg == "--timeout" && i + 1 < argc) {
            try {
                config.max_time_ms = eternity2_utils::safe_stoul(argv[++i]);
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid timeout value: " + std::string(e.what()));
            }
        } else if (arg == "--parallel") {
            config.parallel_enabled = true;
            if (config.num_threads <= 1) {
                config.num_threads = 0;  // 0 = auto-detect
            }
        } else if (arg == "--threads" && i + 1 < argc) {
            try {
                config.num_threads = eternity2_utils::safe_stoul(argv[++i]);
                if (config.num_threads > 1) {
                    config.parallel_enabled = true;
                }
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid thread count: " + std::string(e.what()));
            }
        } else if (arg == "--partition-depth" && i + 1 < argc) {
            try {
                partition_depth = eternity2_utils::safe_stoul(argv[++i]);
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid partition depth: " + std::string(e.what()));
            }
        } else if (arg == "--export-partial") {
            config.export_partial = true;
        } else if (arg == "--export-dir" && i + 1 < argc) {
            config.export_dir = argv[++i];
        } else if (arg == "--export-prefix" && i + 1 < argc) {
            config.export_prefix = argv[++i];
        } else if (arg[0] != '-') {
            filename = arg;
        } else {
            throw std::runtime_error("Unknown option: " + arg);
        }
    }

    if (filename.empty()) {
        throw std::runtime_error("No puzzle file specified");
    }

    return true;
}

/**
 * @brief Execute the DLX solver
 */
SolveResult execute_solver(const SolverConfig& config,
                           const std::pair<Board, std::vector<Piece>>& board_pieces,
                           size_t board_size,
                           bool quiet,
                           bool print_stats,
                           const std::string& puzzle_name,
                           size_t partition_depth) {
    // Setup shared data
    std::mutex mutex;
    Board max_board = create_board(static_cast<int>(board_size));

    SharedData shared_data;
    shared_data.max_board = max_board;
    shared_data.config = config;
    shared_data.puzzle_name = puzzle_name;

    // Progress callback
    auto progress_start = std::chrono::high_resolution_clock::now();
    if (config.verbose) {
        shared_data.on_board_update = [&](const Board& board) {
            static long long last_count = -1;
            if (shared_data.max_count.load() > last_count) {
                last_count = shared_data.max_count.load();
                auto now = std::chrono::high_resolution_clock::now();
                auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - progress_start).count();
                eternity2_logger::info("[{}ms] Progress: {}/{} pieces placed",
                                       elapsed_ms, last_count, board_size * board_size);
            }
        };
    }

    // Start timer
    auto start = std::chrono::high_resolution_clock::now();

    // Create and run solver (parallel or single-threaded)
    SolveResult result;
    if (config.parallel_enabled) {
        ParallelDLXSolver solver(board_pieces.second, board_size, shared_data);
        if (partition_depth > 0) {
            solver.set_partition_depth(partition_depth);
        }
        result = solver.solve();
    } else {
        DLXSolver solver(board_pieces.second, board_size, shared_data);
        result = solver.solve();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    // Output result
    if (result == SolveResult::SOLVED) {
        if (!quiet) {
            eternity2_logger::info("=== SOLUTION FOUND ===");
        }
        std::cout << "==" << std::endl;
        std::string solution_csv = export_board_to_csv_string(shared_data.max_board, puzzle_name);
        std::cout << solution_csv;
        std::cout << "=time=" << elapsed.count() << std::endl;

        // Export solution to file if export directory is set
        if (config.export_partial && !config.export_dir.empty()) {
            std::ostringstream filename;
            filename << config.export_dir << "/"
                     << config.export_prefix << "_solution.csv";
            
            std::ofstream file(filename.str());
            if (file.is_open()) {
                file << solution_csv;
                file << "=time=" << elapsed.count() << std::endl;
                file.close();
                if (config.verbose) {
                    std::cout << "Exported solution to " << filename.str() << std::endl;
                }
            } else {
                std::cerr << "Warning: Failed to open file for solution export: " << filename.str() << std::endl;
            }
        }
    } else {
        if (!quiet) {
            eternity2_logger::info("Result: {}", solve_result_to_string(result));
            eternity2_logger::info("Best: {}/{} pieces",
                                   shared_data.stats.best_depth.load(),
                                   board_size * board_size);
        }
    }

    // Print statistics
    if (print_stats && !quiet) {
        const auto& stats = shared_data.stats;
        eternity2_logger::info("=== Statistics ===");
        eternity2_logger::info("Nodes explored: {}", stats.nodes_explored.load());
        eternity2_logger::info("Backtracks: {}", stats.backtracks.load());
        eternity2_logger::info("Edge incompatible: {}", stats.edge_incompatible.load());
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
    SolverConfig config;
    bool print_stats = true;
    bool quiet = false;
    size_t partition_depth = 0;
    std::string filename;

    try {
        if (!parse_v3_arguments(argc, argv, config, filename, print_stats, quiet, partition_depth)) {
            return 0;  // Help was requested
        }
    } catch (const std::exception& e) {
        eternity2_logger::error("{}", e.what());
        print_v3_usage(argv[0]);
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

    // Set num_threads to hardware concurrency if auto-detect
    if (config.parallel_enabled && config.num_threads == 0) {
        config.num_threads = std::thread::hardware_concurrency();
        if (config.num_threads == 0) {
            config.num_threads = 4;  // Fallback
        }
    }

    if (!quiet) {
        eternity2_logger::info("Puzzle size: {}x{}", board_size, board_size);
        eternity2_logger::info("Pieces: {}", board_pieces.second.size());
        eternity2_logger::info("Solver: Dancing Links (DLX)");
        eternity2_logger::info("Configuration:");
        eternity2_logger::info("  S-heuristic: {}", config.use_s_heuristic ? "enabled" : "disabled");
        eternity2_logger::info("  Edge propagation: {}", config.use_edge_propagation ? "enabled" : "disabled");
        if (config.parallel_enabled) {
            eternity2_logger::info("  Parallel: enabled ({} threads)", config.num_threads);
        } else {
            eternity2_logger::info("  Parallel: disabled (single-threaded)");
        }
        if (config.max_time_ms > 0) {
            eternity2_logger::info("  Timeout: {} ms", config.max_time_ms);
        }
        eternity2_logger::info("Solving...");
    }

    // Extract puzzle name for BUCAS URL
    std::string puzzle_name = extract_puzzle_name(filename);
    config.puzzle_name = puzzle_name;

    // Execute solver
    auto result = execute_solver(config, board_pieces, board_size, quiet, print_stats, puzzle_name, partition_depth);

    return (result == SolveResult::SOLVED) ? 0 : 1;
}
