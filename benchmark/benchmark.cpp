#include "benchmark.h"
#include "../solver/piece_loader/piece_loader.h"
#include "../solver/board/board.h"
#include "../solver/solver/solver.h"
#include "../solver_v2/solver/solver_v2.h"
#include "../solver_v2/parallel/parallel_solver.h"

#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <thread>
#include <mutex>
#include <atomic>
#include <unordered_set>
#include <algorithm>
#include <numeric>
#include <limits>
#include <chrono>
#include <filesystem>
#include <cstring>

namespace eternity2_benchmark {

Benchmark::Benchmark(const BenchmarkConfig& config) : config_(config) {}

BenchmarkResult Benchmark::run_v1(const std::string& puzzle_file) {
    BenchmarkResult result;
    result.solver_name = "V1 (Baseline)";
    result.puzzle_file = puzzle_file;
    result.solved = false;
    result.pieces_placed = 0;
    result.nodes_explored = 0;
    result.backtracks = 0;
    result.hash_hits = 0;
    result.domain_wipeouts = 0;

    try {
        // Load puzzle
        auto board_pieces = load_from_csv(puzzle_file);
        result.board_size = board_pieces.first.size;
        size_t target_pieces = result.board_size * result.board_size;

        // Setup shared data
        Board max_board = create_board(static_cast<int>(result.board_size));
        std::mutex mutex;
        std::unordered_set<BoardHash> hashes;
        long long max_count = 0;

        SharedData shared_data = {
            max_board,
            max_count,
            mutex,
            hashes
        };
        shared_data.on_board_update = [](const Board&) {};

        // Start timing
        auto start = std::chrono::high_resolution_clock::now();

        // Run solver in a separate thread with timeout
        std::atomic<bool> finished{false};
        Board board = board_pieces.first;  // Make a copy for the solver
        std::thread solver_thread([&]() {
            solve_board(board, board_pieces.second, shared_data);
            finished = true;
        });

        // Wait with timeout
        auto timeout = std::chrono::milliseconds(config_.timeout_ms);
        auto deadline = start + timeout;

        while (!finished && std::chrono::high_resolution_clock::now() < deadline) {
            if (shared_data.max_count >= static_cast<long long>(target_pieces)) {
                shared_data.stop = true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        // Stop solver
        shared_data.stop = true;

        if (solver_thread.joinable()) {
            solver_thread.join();
        }

        auto end = std::chrono::high_resolution_clock::now();

        // Collect results
        result.elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();
        result.pieces_placed = static_cast<size_t>(shared_data.max_count.load());
        result.solved = (result.pieces_placed >= target_pieces);
        result.nodes_explored = static_cast<size_t>(shared_data.board_count.load());
        result.hash_hits = static_cast<size_t>(shared_data.hash_hit_count.load());

        // V1 doesn't track backtracks directly, estimate from pieces_placed operations
        // board_count is effectively nodes explored
        result.backtracks = 0; // V1 doesn't track this
        
        // Store solution board if solved
        if (result.solved) {
            result.solution_board = shared_data.max_board;
        }

    } catch (const std::exception& e) {
        if (config_.verbose) {
            std::cerr << "V1 error on " << puzzle_file << ": " << e.what() << std::endl;
        }
    }

    return result;
}

BenchmarkResult Benchmark::run_v2(const std::string& puzzle_file) {
    BenchmarkResult result;
    result.solver_name = "V2 (MAC+MRV+LCV)";
    result.puzzle_file = puzzle_file;
    result.solved = false;
    result.pieces_placed = 0;
    result.nodes_explored = 0;
    result.backtracks = 0;
    result.hash_hits = 0;
    result.domain_wipeouts = 0;

    try {
        // Load puzzle
        auto board_pieces = load_from_csv(puzzle_file);
        result.board_size = board_pieces.first.size;

        // Setup shared data
        std::mutex mutex;
        Board max_board = create_board(static_cast<int>(result.board_size));

        eternity2_v2::SharedDataV2 shared_data = {
            max_board,
            {0},
            mutex
        };

        // Configure heuristics
        shared_data.config.use_mrv = config_.v2_use_mrv;
        shared_data.config.use_degree = config_.v2_use_degree;
        shared_data.config.use_lcv = config_.v2_use_lcv;
        shared_data.config.max_time_ms = config_.timeout_ms;
        shared_data.config.collect_stats = true;
        shared_data.config.verbose = false;

        // Start timing
        auto start = std::chrono::high_resolution_clock::now();

        // Run solver
        eternity2_v2::SolverV2 solver(board_pieces.second, result.board_size, shared_data);
        eternity2_v2::SolveResult solve_result = solver.solve();

        auto end = std::chrono::high_resolution_clock::now();

        // Collect results
        const auto& stats = solver.get_stats();
        result.elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();
        result.pieces_placed = static_cast<size_t>(shared_data.max_count.load());
        result.solved = (solve_result == eternity2_v2::SolveResult::SOLVED);
        result.nodes_explored = stats.nodes_explored.load();
        result.backtracks = stats.backtracks.load();
        result.domain_wipeouts = stats.domain_wipeouts.load();
        
        // Store solution board if solved
        if (result.solved) {
            result.solution_board = solver.get_solution();
        }

    } catch (const std::exception& e) {
        if (config_.verbose) {
            std::cerr << "V2 error on " << puzzle_file << ": " << e.what() << std::endl;
        }
    }

    return result;
}

BenchmarkResult Benchmark::run_v2_parallel(const std::string& puzzle_file) {
    BenchmarkResult result;

    // Determine thread count
    size_t num_threads = config_.v2_num_threads;
    if (num_threads == 0) {
        num_threads = std::thread::hardware_concurrency();
        if (num_threads == 0) {
            num_threads = 4;  // Fallback
        }
    }

    result.solver_name = "V2 Parallel (" + std::to_string(num_threads) + " threads)";
    result.puzzle_file = puzzle_file;
    result.solved = false;
    result.pieces_placed = 0;
    result.nodes_explored = 0;
    result.backtracks = 0;
    result.hash_hits = 0;
    result.domain_wipeouts = 0;

    try {
        // Load puzzle
        auto board_pieces = load_from_csv(puzzle_file);
        result.board_size = board_pieces.first.size;

        // Setup shared data
        std::mutex mutex;
        Board max_board = create_board(static_cast<int>(result.board_size));

        eternity2_v2::SharedDataV2 shared_data = {
            max_board,
            {0},
            mutex
        };

        // Configure heuristics and parallel mode
        shared_data.config.use_mrv = config_.v2_use_mrv;
        shared_data.config.use_degree = config_.v2_use_degree;
        shared_data.config.use_lcv = config_.v2_use_lcv;
        shared_data.config.max_time_ms = config_.timeout_ms;
        shared_data.config.collect_stats = true;
        shared_data.config.verbose = false;
        shared_data.config.parallel_enabled = true;
        shared_data.config.num_threads = num_threads;

        // Start timing
        auto start = std::chrono::high_resolution_clock::now();

        // Run parallel solver
        eternity2_v2::ParallelSolverV2 solver(board_pieces.second, result.board_size, shared_data);
        eternity2_v2::SolveResult solve_result = solver.solve();

        auto end = std::chrono::high_resolution_clock::now();

        // Collect results
        const auto& stats = shared_data.stats;
        result.elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();
        result.pieces_placed = static_cast<size_t>(shared_data.max_count.load());
        result.solved = (solve_result == eternity2_v2::SolveResult::SOLVED);
        result.nodes_explored = stats.nodes_explored.load();
        result.backtracks = stats.backtracks.load();
        result.domain_wipeouts = stats.domain_wipeouts.load();

        // Store solution board if solved
        if (result.solved) {
            result.solution_board = shared_data.max_board;
        }

    } catch (const std::exception& e) {
        if (config_.verbose) {
            std::cerr << "V2 Parallel error on " << puzzle_file << ": " << e.what() << std::endl;
        }
    }

    return result;
}

BenchmarkComparison Benchmark::run_comparison(const std::string& puzzle_file) {
    BenchmarkComparison comparison;
    comparison.puzzle_file = puzzle_file;

    // Run V1 (if enabled)
    if (config_.run_v1) {
        comparison.v1_result = run_v1(puzzle_file);
    } else {
        comparison.v1_result.puzzle_file = puzzle_file;
        comparison.v1_result.solver_name = "V1 (Skipped)";
    }

    // Run V2 single-threaded (if enabled)
    if (config_.run_v2) {
        comparison.v2_result = run_v2(puzzle_file);
    } else {
        comparison.v2_result.puzzle_file = puzzle_file;
        comparison.v2_result.solver_name = "V2 (Skipped)";
    }

    // Run V2 parallel (if enabled)
    if (config_.run_v2_parallel) {
        comparison.v2_parallel_result = run_v2_parallel(puzzle_file);
    } else {
        comparison.v2_parallel_result.puzzle_file = puzzle_file;
        comparison.v2_parallel_result.solver_name = "V2 Parallel (Skipped)";
    }

    // Set board size from whichever solver ran
    comparison.board_size = config_.run_v1 ? comparison.v1_result.board_size
                                           : comparison.v2_result.board_size;
    
    // Export solutions if configured
    if (config_.export_solutions) {
        // Create solutions directory at the same level as the puzzle file
        namespace fs = std::filesystem;
        fs::path puzzle_path(comparison.puzzle_file);
        fs::path puzzle_dir = puzzle_path.parent_path();
        fs::path solutions_dir = puzzle_dir / "solutions";
        
        std::string v1_dir = (solutions_dir / "v1").string();
        std::string v2_dir = (solutions_dir / "v2").string();
        
        if (comparison.v1_result.solved && comparison.v1_result.solution_board.has_value()) {
            Benchmark::export_solution(comparison.v1_result, v1_dir);
            if (config_.verbose) {
                std::cout << "  V1 solution exported to: " << v1_dir << std::endl;
            }
        }
        if (comparison.v2_result.solved && comparison.v2_result.solution_board.has_value()) {
            Benchmark::export_solution(comparison.v2_result, v2_dir);
            if (config_.verbose) {
                std::cout << "  V2 solution exported to: " << v2_dir << std::endl;
            }
        }
    }

    return comparison;
}

std::vector<BenchmarkComparison> Benchmark::run_all(const std::vector<std::string>& puzzle_files) {
    std::vector<BenchmarkComparison> results;
    results.resize(puzzle_files.size());

    // Sequential mode
    if (!config_.parallel) {
        if (config_.show_progress) {
            std::cout << "Processing " << puzzle_files.size() << " puzzle(s) sequentially" << std::endl;
        }

        for (size_t i = 0; i < puzzle_files.size(); ++i) {
            if (config_.show_progress) {
                std::cout << "[" << (i + 1) << "/" << puzzle_files.size() << "] "
                          << "Benchmarking: " << puzzle_files[i] << "..." << std::flush;
            }

            results[i] = run_comparison(puzzle_files[i]);

            if (config_.show_progress) {
                std::cout << " done";
                if (config_.verbose) {
                    std::cout << " (V1: " << std::fixed << std::setprecision(1)
                              << results[i].v1_result.elapsed_ms << "ms, V2: "
                              << results[i].v2_result.elapsed_ms << "ms)";
                }
                std::cout << std::endl;
            }
        }

        return results;
    }

    // Parallel mode
    size_t num_threads = std::thread::hardware_concurrency();
    if (num_threads == 0) {
        num_threads = 4;  // Fallback if hardware_concurrency() returns 0
    }
    // Don't use more threads than puzzles
    num_threads = std::min(num_threads, puzzle_files.size());

    if (config_.show_progress) {
        std::cout << "Processing " << puzzle_files.size() << " puzzle(s) using " << num_threads << " thread(s)" << std::endl;
    }

    // Thread pool approach: process puzzles in parallel
    std::vector<std::thread> threads;
    threads.reserve(num_threads);
    std::atomic<size_t> next_index{0};
    std::atomic<size_t> completed_count{0};
    std::mutex progress_mutex;

    // Launch worker threads
    for (size_t t = 0; t < num_threads; ++t) {
        threads.emplace_back([&]() {
            while (true) {
                size_t i = next_index.fetch_add(1);
                if (i >= puzzle_files.size()) {
                    break;  // No more puzzles to process
                }

                // Run comparison for this puzzle
                results[i] = run_comparison(puzzle_files[i]);

                // Print progress (thread-safe)
                if (config_.show_progress) {
                    size_t done = completed_count.fetch_add(1) + 1;
                    std::lock_guard<std::mutex> lock(progress_mutex);
                    std::cout << "[" << done << "/" << puzzle_files.size() << "] "
                              << puzzle_files[i] << " completed" << std::endl;
                }
            }
        });
    }

    // Wait for all threads to complete
    for (auto& thread : threads) {
        thread.join();
    }

    return results;
}

BenchmarkSummary Benchmark::summarize(const std::vector<BenchmarkComparison>& results) {
    BenchmarkSummary summary = {};
    summary.total_puzzles = results.size();
    summary.max_speedup = 0;
    summary.min_speedup = std::numeric_limits<double>::max();

    double total_speedup = 0;
    double total_node_reduction = 0;
    size_t both_solved_count = 0;

    for (const auto& comp : results) {
        if (comp.v1_result.solved) summary.v1_solved++;
        if (comp.v2_result.solved) summary.v2_solved++;

        summary.total_v1_nodes += comp.v1_result.nodes_explored;
        summary.total_v2_nodes += comp.v2_result.nodes_explored;
        summary.total_v1_backtracks += comp.v1_result.backtracks;
        summary.total_v2_backtracks += comp.v2_result.backtracks;

        summary.avg_v1_time_ms += comp.v1_result.elapsed_ms;
        summary.avg_v2_time_ms += comp.v2_result.elapsed_ms;

        // Only calculate speedup for puzzles both solved
        if (comp.v1_result.solved && comp.v2_result.solved) {
            double speedup = comp.speedup();
            double node_reduction = comp.node_reduction();

            total_speedup += speedup;
            total_node_reduction += node_reduction;
            both_solved_count++;

            if (speedup > summary.max_speedup) {
                summary.max_speedup = speedup;
                summary.max_speedup_puzzle = comp.puzzle_file;
            }
            if (speedup < summary.min_speedup) {
                summary.min_speedup = speedup;
                summary.min_speedup_puzzle = comp.puzzle_file;
            }
        }
    }

    if (!results.empty()) {
        summary.avg_v1_time_ms /= results.size();
        summary.avg_v2_time_ms /= results.size();
    }

    if (both_solved_count > 0) {
        summary.avg_speedup = total_speedup / both_solved_count;
        summary.avg_node_reduction = total_node_reduction / both_solved_count;
    }

    if (summary.min_speedup == std::numeric_limits<double>::max()) {
        summary.min_speedup = 0;
    }

    return summary;
}

void Benchmark::print_result(const BenchmarkResult& result) {
    std::cout << "Solver: " << result.solver_name << std::endl;
    std::cout << "  Puzzle: " << result.puzzle_file << std::endl;
    std::cout << "  Board size: " << result.board_size << "x" << result.board_size << std::endl;
    std::cout << "  Status: " << (result.solved ? "SOLVED" : "NOT SOLVED") << std::endl;
    std::cout << "  Pieces placed: " << result.pieces_placed
              << "/" << (result.board_size * result.board_size) << std::endl;
    std::cout << "  Time: " << std::fixed << std::setprecision(2) << result.elapsed_ms << " ms" << std::endl;
    std::cout << "  Nodes explored: " << result.nodes_explored << std::endl;
    std::cout << "  Backtracks: " << result.backtracks << std::endl;
    if (result.hash_hits > 0) {
        std::cout << "  Hash hits: " << result.hash_hits << std::endl;
    }
    if (result.domain_wipeouts > 0) {
        std::cout << "  Domain wipeouts: " << result.domain_wipeouts << std::endl;
    }
    std::cout << "  Nodes/ms: " << std::fixed << std::setprecision(1) << result.nodes_per_ms() << std::endl;
}

void Benchmark::print_comparison(const BenchmarkComparison& comparison) {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "BENCHMARK COMPARISON" << std::endl;
    std::cout << "Puzzle: " << comparison.puzzle_file << std::endl;
    std::cout << "Board: " << comparison.board_size << "x" << comparison.board_size << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    std::cout << "\n--- V1 (Baseline) ---" << std::endl;
    std::cout << "  Status: " << (comparison.v1_result.solved ? "SOLVED" : "NOT SOLVED") << std::endl;
    std::cout << "  Time: " << std::fixed << std::setprecision(2)
              << comparison.v1_result.elapsed_ms << " ms" << std::endl;
    std::cout << "  Nodes: " << comparison.v1_result.nodes_explored << std::endl;
    std::cout << "  Hash hits: " << comparison.v1_result.hash_hits << std::endl;

    std::cout << "\n--- V2 (MAC+MRV+LCV) ---" << std::endl;
    std::cout << "  Status: " << (comparison.v2_result.solved ? "SOLVED" : "NOT SOLVED") << std::endl;
    std::cout << "  Time: " << std::fixed << std::setprecision(2)
              << comparison.v2_result.elapsed_ms << " ms" << std::endl;
    std::cout << "  Nodes: " << comparison.v2_result.nodes_explored << std::endl;
    std::cout << "  Backtracks: " << comparison.v2_result.backtracks << std::endl;
    std::cout << "  Domain wipeouts: " << comparison.v2_result.domain_wipeouts << std::endl;

    if (comparison.v1_result.solved && comparison.v2_result.solved) {
        std::cout << "\n--- COMPARISON ---" << std::endl;
        double speedup = comparison.speedup();
        double node_reduction = comparison.node_reduction();

        std::cout << "  Speedup: " << std::fixed << std::setprecision(2) << speedup << "x";
        if (speedup >= 1.0) {
            std::cout << " (V2 is faster)";
        } else {
            std::cout << " (V1 is faster)";
        }
        std::cout << std::endl;

        std::cout << "  Node reduction: " << std::fixed << std::setprecision(2)
                  << node_reduction << "x";
        if (node_reduction >= 1.0) {
            std::cout << " (V2 explores fewer nodes)";
        }
        std::cout << std::endl;
    }
}

void Benchmark::print_table(const std::vector<BenchmarkComparison>& comparisons) {
    if (comparisons.empty()) return;

    // Header
    std::cout << "\n" << std::string(120, '=') << std::endl;
    std::cout << "BENCHMARK RESULTS TABLE" << std::endl;
    std::cout << std::string(120, '=') << std::endl;

    // Column headers
    std::cout << std::left << std::setw(30) << "Puzzle"
              << std::right << std::setw(6) << "Size"
              << std::setw(12) << "V1 Time"
              << std::setw(12) << "V2 Time"
              << std::setw(10) << "Speedup"
              << std::setw(12) << "V1 Nodes"
              << std::setw(12) << "V2 Nodes"
              << std::setw(12) << "Node Red."
              << std::setw(8) << "V1"
              << std::setw(8) << "V2"
              << std::endl;

    std::cout << std::left << std::setw(30) << ""
              << std::right << std::setw(6) << ""
              << std::setw(12) << "(ms)"
              << std::setw(12) << "(ms)"
              << std::setw(10) << ""
              << std::setw(12) << ""
              << std::setw(12) << ""
              << std::setw(12) << ""
              << std::setw(8) << "Solved"
              << std::setw(8) << "Solved"
              << std::endl;

    std::cout << std::string(120, '-') << std::endl;

    // Data rows
    for (const auto& comp : comparisons) {
        // Extract filename from path
        std::string filename = comp.puzzle_file;
        size_t pos = filename.find_last_of("/\\");
        if (pos != std::string::npos) {
            filename = filename.substr(pos + 1);
        }
        if (filename.length() > 28) {
            filename = filename.substr(0, 25) + "...";
        }

        std::cout << std::left << std::setw(30) << filename
                  << std::right << std::setw(6) << (std::to_string(comp.board_size) + "x" + std::to_string(comp.board_size));

        std::cout << std::fixed << std::setprecision(2)
                  << std::setw(12) << comp.v1_result.elapsed_ms
                  << std::setw(12) << comp.v2_result.elapsed_ms;

        if (comp.v1_result.solved && comp.v2_result.solved) {
            std::ostringstream speedup_str;
            speedup_str << std::fixed << std::setprecision(1) << comp.speedup() << "x";
            std::cout << std::setw(10) << speedup_str.str();
        } else {
            std::cout << std::setw(10) << "-";
        }

        std::cout << std::setw(12) << comp.v1_result.nodes_explored
                  << std::setw(12) << comp.v2_result.nodes_explored;

        if (comp.v1_result.solved && comp.v2_result.solved && comp.v2_result.nodes_explored > 0) {
            std::ostringstream reduction_str;
            reduction_str << std::fixed << std::setprecision(1) << comp.node_reduction() << "x";
            std::cout << std::setw(12) << reduction_str.str();
        } else {
            std::cout << std::setw(12) << "-";
        }

        std::cout << std::setw(8) << (comp.v1_result.solved ? "YES" : "NO")
                  << std::setw(8) << (comp.v2_result.solved ? "YES" : "NO")
                  << std::endl;
    }

    std::cout << std::string(120, '=') << std::endl;
}

void Benchmark::print_summary(const BenchmarkSummary& summary) {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "BENCHMARK SUMMARY" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    std::cout << "\nPuzzles tested: " << summary.total_puzzles << std::endl;
    std::cout << "V1 solved: " << summary.v1_solved << "/" << summary.total_puzzles << std::endl;
    std::cout << "V2 solved: " << summary.v2_solved << "/" << summary.total_puzzles << std::endl;

    std::cout << "\n--- Timing ---" << std::endl;
    std::cout << "Average V1 time: " << std::fixed << std::setprecision(2)
              << summary.avg_v1_time_ms << " ms" << std::endl;
    std::cout << "Average V2 time: " << std::fixed << std::setprecision(2)
              << summary.avg_v2_time_ms << " ms" << std::endl;
    std::cout << "Average speedup: " << std::fixed << std::setprecision(2)
              << summary.avg_speedup << "x" << std::endl;

    std::cout << "\n--- Nodes ---" << std::endl;
    std::cout << "Total V1 nodes: " << summary.total_v1_nodes << std::endl;
    std::cout << "Total V2 nodes: " << summary.total_v2_nodes << std::endl;
    std::cout << "Average node reduction: " << std::fixed << std::setprecision(2)
              << summary.avg_node_reduction << "x" << std::endl;

    if (summary.max_speedup > 0) {
        std::cout << "\n--- Best/Worst ---" << std::endl;
        std::cout << "Max speedup: " << std::fixed << std::setprecision(2)
                  << summary.max_speedup << "x (" << summary.max_speedup_puzzle << ")" << std::endl;
        std::cout << "Min speedup: " << std::fixed << std::setprecision(2)
                  << summary.min_speedup << "x (" << summary.min_speedup_puzzle << ")" << std::endl;
    }

    std::cout << std::string(60, '=') << std::endl;
}

std::string Benchmark::to_csv(const std::vector<BenchmarkComparison>& comparisons) {
    std::ostringstream csv;

    // Header
    csv << "puzzle_file,board_size,"
        << "v1_solved,v1_time_ms,v1_nodes,v1_hash_hits,"
        << "v2_solved,v2_time_ms,v2_nodes,v2_backtracks,v2_domain_wipeouts,"
        << "speedup,node_reduction\n";

    // Data
    for (const auto& comp : comparisons) {
        csv << "\"" << comp.puzzle_file << "\","
            << comp.board_size << ","
            << (comp.v1_result.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v1_result.elapsed_ms << ","
            << comp.v1_result.nodes_explored << ","
            << comp.v1_result.hash_hits << ","
            << (comp.v2_result.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v2_result.elapsed_ms << ","
            << comp.v2_result.nodes_explored << ","
            << comp.v2_result.backtracks << ","
            << comp.v2_result.domain_wipeouts << ",";

        if (comp.v1_result.solved && comp.v2_result.solved) {
            csv << std::fixed << std::setprecision(4) << comp.speedup() << ","
                << std::fixed << std::setprecision(4) << comp.node_reduction();
        } else {
            csv << ",";
        }
        csv << "\n";
    }

    return csv.str();
}

void Benchmark::export_csv(const std::vector<BenchmarkComparison>& comparisons,
                          const std::string& output_file) {
    std::ofstream file(output_file);
    if (file.is_open()) {
        file << to_csv(comparisons);
        file.close();
        std::cout << "Results exported to: " << output_file << std::endl;
    } else {
        std::cerr << "Error: Could not write to " << output_file << std::endl;
    }
}

void Benchmark::export_solution(const BenchmarkResult& result, const std::string& output_dir) {
    if (!result.solved || !result.solution_board.has_value()) {
        return;
    }
    
    namespace fs = std::filesystem;
    
    // Create output directory if it doesn't exist
    try {
        fs::create_directories(output_dir);
    } catch (const std::exception& e) {
        std::cerr << "Error creating directory " << output_dir << ": " << e.what() << std::endl;
        return;
    }
    
    // Extract puzzle filename
    std::string puzzle_name = result.puzzle_file;
    size_t pos = puzzle_name.find_last_of("/\\");
    if (pos != std::string::npos) {
        puzzle_name = puzzle_name.substr(pos + 1);
    }
    
    // Remove .csv extension if present
    if (puzzle_name.size() > 4 && puzzle_name.substr(puzzle_name.size() - 4) == ".csv") {
        puzzle_name = puzzle_name.substr(0, puzzle_name.size() - 4);
    }
    
    // Create output filename
    std::string output_file = output_dir + "/" + puzzle_name + "_solved.csv";
    
    // Export the solution
    std::string solution_csv = export_board_to_csv_string(result.solution_board.value());
    
    std::ofstream file(output_file);
    if (file.is_open()) {
        file << solution_csv;
        file.close();
        // Note: verbose output removed from static function
    } else {
        std::cerr << "Error: Could not write solution to " << output_file << std::endl;
    }
}

void Benchmark::export_all_solutions(const std::vector<BenchmarkComparison>& comparisons,
                                    const std::string& output_dir) {
    namespace fs = std::filesystem;
    
    // Create base output directory
    try {
        fs::create_directories(output_dir);
        fs::create_directories(output_dir + "/v1");
        fs::create_directories(output_dir + "/v2");
    } catch (const std::exception& e) {
        std::cerr << "Error creating directories: " << e.what() << std::endl;
        return;
    }
    
    // Export all solutions
    for (const auto& comp : comparisons) {
        if (comp.v1_result.solved && comp.v1_result.solution_board.has_value()) {
            export_solution(comp.v1_result, output_dir + "/v1");
        }
        if (comp.v2_result.solved && comp.v2_result.solution_board.has_value()) {
            export_solution(comp.v2_result, output_dir + "/v2");
        }
    }
    
    std::cout << "All solutions exported to: " << output_dir << std::endl;
}

} // namespace eternity2_benchmark
