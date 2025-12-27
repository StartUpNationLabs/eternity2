#include "benchmark.h"
#include "common/piece_loader.h"
#include "v0/solver_v0.h"
#include "v1/board/board.h"
#include "v1/solver/solver.h"
#include "v2/solver/solver_v2.h"
#include "v2/parallel/parallel_solver.h"

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
#include <map>

namespace eternity2_benchmark {

Benchmark::Benchmark(const BenchmarkConfig& config) : config_(config) {}

BenchmarkResult Benchmark::run_v0(const std::string& puzzle_file) {
    BenchmarkResult result;
    result.solver_name = "V0 (Simple Backtracking)";
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

        // Setup shared data for v0
        Board max_board = create_board(static_cast<int>(result.board_size));
        std::mutex mutex;
        std::unordered_set<BoardHash> hashes;

        eternity2_v0::SharedDataV0 shared_data = {
            max_board,
            {0},
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
            eternity2_v0::solve_board(board, board_pieces.second, shared_data);
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
        result.backtracks = 0; // V0 doesn't track this separately

        // Store solution board if solved
        if (result.solved) {
            result.solution_board = shared_data.max_board;
        }

    } catch (const std::exception& e) {
        if (config_.verbose) {
            std::cerr << "V0 error on " << puzzle_file << ": " << e.what() << std::endl;
        }
    }

    return result;
}

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

BenchmarkResult Benchmark::run_v1_parallel(const std::string& puzzle_file) {
    BenchmarkResult result;
    result.solver_name = "V1 Parallel";
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

        // Determine thread count
        size_t thread_count = config_.v1_parallel_thread_count;
        if (thread_count == 0) {
            thread_count = std::thread::hardware_concurrency();
            if (thread_count == 0) thread_count = 4; // fallback
        }

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

        // Launch worker threads
        std::vector<std::thread> threads;
        threads.reserve(thread_count);

        for (size_t i = 0; i < thread_count; ++i) {
            threads.emplace_back([&, i]() {
                Board board_copy = board_pieces.first;
                std::vector<Piece> pieces_copy = board_pieces.second;
                solve_board(board_copy, pieces_copy, shared_data);
            });
        }

        // Monitor progress with timeout
        auto timeout = std::chrono::milliseconds(config_.timeout_ms);
        auto deadline = start + timeout;

        while (std::chrono::high_resolution_clock::now() < deadline) {
            if (shared_data.max_count >= static_cast<long long>(target_pieces)) {
                shared_data.stop = true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        // Stop all threads
        shared_data.stop = true;

        // Join all threads
        for (auto& thread : threads) {
            if (thread.joinable()) {
                thread.join();
            }
        }

        auto end = std::chrono::high_resolution_clock::now();

        // Collect results
        result.elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();
        result.pieces_placed = static_cast<size_t>(shared_data.max_count.load());
        result.solved = (result.pieces_placed >= target_pieces);
        result.nodes_explored = static_cast<size_t>(shared_data.board_count.load());
        result.hash_hits = static_cast<size_t>(shared_data.hash_hit_count.load());
        result.backtracks = 0; // V1 doesn't track this

        // Store solution board if solved
        if (result.solved) {
            result.solution_board = shared_data.max_board;
        }

    } catch (const std::exception& e) {
        if (config_.verbose) {
            std::cerr << "V1 Parallel error on " << puzzle_file << ": " << e.what() << std::endl;
        }
    }

    return result;
}

BenchmarkResult Benchmark::run_v2(const std::string& puzzle_file, bool border_first) {
    BenchmarkResult result;
    result.solver_name = border_first ? "V2 Border-First" : "V2 Standard";
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
        shared_data.config.strategy = border_first ?
            eternity2_v2::SolveStrategy::BORDER_FIRST :
            eternity2_v2::SolveStrategy::STANDARD;
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

BenchmarkResult Benchmark::run_v2_parallel(const std::string& puzzle_file, bool border_first) {
    BenchmarkResult result;

    // Determine thread count
    size_t num_threads = config_.v2_num_threads;
    if (num_threads == 0) {
        num_threads = std::thread::hardware_concurrency();
        if (num_threads == 0) {
            num_threads = 4;  // Fallback
        }
    }

    result.solver_name = border_first ?
        "V2 Parallel Border-First (" + std::to_string(num_threads) + " threads)" :
        "V2 Parallel (" + std::to_string(num_threads) + " threads)";
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
        shared_data.config.strategy = border_first ?
            eternity2_v2::SolveStrategy::BORDER_FIRST :
            eternity2_v2::SolveStrategy::STANDARD;
        shared_data.config.max_time_ms = config_.timeout_ms;
        shared_data.config.collect_stats = true;
        shared_data.config.verbose = config_.verbose;  // Pass through verbose flag
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

    // Run V0 (if enabled)
    if (config_.run_v0) {
        comparison.v0_result = run_v0(puzzle_file);
    } else {
        comparison.v0_result.puzzle_file = puzzle_file;
        comparison.v0_result.solver_name = "V0 (Skipped)";
    }

    // Run V1 (if enabled)
    if (config_.run_v1) {
        comparison.v1_result = run_v1(puzzle_file);
    } else {
        comparison.v1_result.puzzle_file = puzzle_file;
        comparison.v1_result.solver_name = "V1 (Skipped)";
    }

    // Run V1 parallel (if enabled)
    if (config_.run_v1_parallel) {
        comparison.v1_parallel = run_v1_parallel(puzzle_file);
    } else {
        comparison.v1_parallel.puzzle_file = puzzle_file;
        comparison.v1_parallel.solver_name = "V1 Parallel (Skipped)";
    }

    // Run V2 standard (if enabled)
    if (config_.run_v2_standard) {
        comparison.v2_standard = run_v2(puzzle_file, false);
    } else {
        comparison.v2_standard.puzzle_file = puzzle_file;
        comparison.v2_standard.solver_name = "V2 Standard (Skipped)";
    }

    // Run V2 border-first (if enabled)
    if (config_.run_v2_border_first) {
        comparison.v2_border_first = run_v2(puzzle_file, true);
    } else {
        comparison.v2_border_first.puzzle_file = puzzle_file;
        comparison.v2_border_first.solver_name = "V2 Border-First (Skipped)";
    }

    // Run V2 parallel (if enabled)
    if (config_.run_v2_parallel) {
        comparison.v2_parallel = run_v2_parallel(puzzle_file, false);
    } else {
        comparison.v2_parallel.puzzle_file = puzzle_file;
        comparison.v2_parallel.solver_name = "V2 Parallel (Skipped)";
    }

    // Run V2 parallel border-first (if enabled)
    if (config_.run_v2_parallel_border_first) {
        comparison.v2_parallel_border_first = run_v2_parallel(puzzle_file, true);
    } else {
        comparison.v2_parallel_border_first.puzzle_file = puzzle_file;
        comparison.v2_parallel_border_first.solver_name = "V2 Parallel Border-First (Skipped)";
    }

    // Set board size from whichever solver ran
    comparison.board_size = config_.run_v0 ? comparison.v0_result.board_size
                          : (config_.run_v1 ? comparison.v1_result.board_size
                          : (config_.run_v2_standard ? comparison.v2_standard.board_size
                          : (config_.run_v2_border_first ? comparison.v2_border_first.board_size
                          : (config_.run_v2_parallel ? comparison.v2_parallel.board_size
                                                     : comparison.v2_parallel_border_first.board_size))));
    
    // Export solutions if configured
    if (config_.export_solutions) {
        // Create solutions directory at the same level as the puzzle file
        namespace fs = std::filesystem;
        fs::path puzzle_path(comparison.puzzle_file);
        fs::path puzzle_dir = puzzle_path.parent_path();
        fs::path solutions_dir = puzzle_dir / "solutions";

        if (comparison.v0_result.solved && comparison.v0_result.solution_board.has_value()) {
            std::string v0_dir = (solutions_dir / "v0").string();
            Benchmark::export_solution(comparison.v0_result, v0_dir);
            if (config_.verbose) {
                std::cout << "  V0 solution exported to: " << v0_dir << std::endl;
            }
        }
        if (comparison.v1_result.solved && comparison.v1_result.solution_board.has_value()) {
            std::string v1_dir = (solutions_dir / "v1").string();
            Benchmark::export_solution(comparison.v1_result, v1_dir);
            if (config_.verbose) {
                std::cout << "  V1 solution exported to: " << v1_dir << std::endl;
            }
        }
        if (comparison.v2_standard.solved && comparison.v2_standard.solution_board.has_value()) {
            std::string v2_dir = (solutions_dir / "v2_standard").string();
            Benchmark::export_solution(comparison.v2_standard, v2_dir);
            if (config_.verbose) {
                std::cout << "  V2 Standard solution exported to: " << v2_dir << std::endl;
            }
        }
        if (comparison.v2_border_first.solved && comparison.v2_border_first.solution_board.has_value()) {
            std::string v2_dir = (solutions_dir / "v2_border_first").string();
            Benchmark::export_solution(comparison.v2_border_first, v2_dir);
            if (config_.verbose) {
                std::cout << "  V2 Border-First solution exported to: " << v2_dir << std::endl;
            }
        }
        if (comparison.v2_parallel.solved && comparison.v2_parallel.solution_board.has_value()) {
            std::string v2_dir = (solutions_dir / "v2_parallel").string();
            Benchmark::export_solution(comparison.v2_parallel, v2_dir);
            if (config_.verbose) {
                std::cout << "  V2 Parallel solution exported to: " << v2_dir << std::endl;
            }
        }
        if (comparison.v2_parallel_border_first.solved && comparison.v2_parallel_border_first.solution_board.has_value()) {
            std::string v2_dir = (solutions_dir / "v2_parallel_border_first").string();
            Benchmark::export_solution(comparison.v2_parallel_border_first, v2_dir);
            if (config_.verbose) {
                std::cout << "  V2 Parallel Border-First solution exported to: " << v2_dir << std::endl;
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
                              << results[i].v1_result.elapsed_ms << "ms, V2-Std: "
                              << results[i].v2_standard.elapsed_ms << "ms)";
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

    double total_best_speedup = 0;
    size_t speedup_count = 0;
    std::map<std::string, size_t> variant_win_count;

    for (const auto& comp : results) {
        // Count solved puzzles
        if (comp.v0_result.solved) summary.v0_solved++;
        if (comp.v1_result.solved) summary.v1_solved++;
        if (comp.v1_parallel.solved) summary.v1_par_solved++;
        if (comp.v2_standard.solved) summary.v2_std_solved++;
        if (comp.v2_border_first.solved) summary.v2_bf_solved++;
        if (comp.v2_parallel.solved) summary.v2_par_solved++;
        if (comp.v2_parallel_border_first.solved) summary.v2_par_bf_solved++;

        // Accumulate times
        summary.avg_v0_time_ms += comp.v0_result.elapsed_ms;
        summary.avg_v1_time_ms += comp.v1_result.elapsed_ms;
        summary.avg_v1_par_time_ms += comp.v1_parallel.elapsed_ms;
        summary.avg_v2_std_time_ms += comp.v2_standard.elapsed_ms;
        summary.avg_v2_bf_time_ms += comp.v2_border_first.elapsed_ms;
        summary.avg_v2_par_time_ms += comp.v2_parallel.elapsed_ms;
        summary.avg_v2_par_bf_time_ms += comp.v2_parallel_border_first.elapsed_ms;

        // Accumulate nodes and backtracks for legacy compatibility
        summary.total_v1_nodes += comp.v1_result.nodes_explored;
        summary.total_v2_nodes += comp.v2_standard.nodes_explored;
        summary.total_v1_backtracks += comp.v1_result.backtracks;
        summary.total_v2_backtracks += comp.v2_standard.backtracks;

        // Calculate best speedup for this puzzle
        if (comp.v1_result.solved && comp.v1_result.elapsed_ms > 0) {
            const auto& best = comp.best_v2();
            if (best.solved && best.elapsed_ms > 0) {
                double speedup = comp.v1_result.elapsed_ms / best.elapsed_ms;
                total_best_speedup += speedup;
                speedup_count++;

                // Track which variant wins
                variant_win_count[best.solver_name]++;

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
    }

    // Calculate averages
    if (!results.empty()) {
        summary.avg_v0_time_ms /= results.size();
        summary.avg_v1_time_ms /= results.size();
        summary.avg_v1_par_time_ms /= results.size();
        summary.avg_v2_std_time_ms /= results.size();
        summary.avg_v2_bf_time_ms /= results.size();
        summary.avg_v2_par_time_ms /= results.size();
        summary.avg_v2_par_bf_time_ms /= results.size();
    }

    if (speedup_count > 0) {
        summary.avg_best_speedup = total_best_speedup / speedup_count;
    }

    if (summary.min_speedup == std::numeric_limits<double>::max()) {
        summary.min_speedup = 0;
    }

    // Find most common best variant
    size_t max_wins = 0;
    for (const auto& [variant, wins] : variant_win_count) {
        if (wins > max_wins) {
            max_wins = wins;
            summary.best_variant_name = variant;
        }
    }

    // Set legacy fields
    summary.v2_solved = summary.v2_std_solved;
    summary.avg_v2_time_ms = summary.avg_v2_std_time_ms;
    summary.avg_speedup = summary.avg_best_speedup;

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

    std::cout << "\n--- V2 Standard (MAC+MRV+LCV) ---" << std::endl;
    std::cout << "  Status: " << (comparison.v2_standard.solved ? "SOLVED" : "NOT SOLVED") << std::endl;
    std::cout << "  Time: " << std::fixed << std::setprecision(2)
              << comparison.v2_standard.elapsed_ms << " ms" << std::endl;
    std::cout << "  Nodes: " << comparison.v2_standard.nodes_explored << std::endl;
    std::cout << "  Backtracks: " << comparison.v2_standard.backtracks << std::endl;
    std::cout << "  Domain wipeouts: " << comparison.v2_standard.domain_wipeouts << std::endl;

    if (comparison.v1_result.solved && comparison.v2_standard.solved) {
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

    // Check which variants have results
    bool has_v0 = false, has_v1 = false, has_v1_par = false, has_v2_std = false, has_v2_bf = false;
    bool has_v2_par = false, has_v2_par_bf = false;

    for (const auto& comp : comparisons) {
        if (comp.v0_result.elapsed_ms > 0) has_v0 = true;
        if (comp.v1_result.elapsed_ms > 0) has_v1 = true;
        if (comp.v1_parallel.elapsed_ms > 0) has_v1_par = true;
        if (comp.v2_standard.elapsed_ms > 0) has_v2_std = true;
        if (comp.v2_border_first.elapsed_ms > 0) has_v2_bf = true;
        if (comp.v2_parallel.elapsed_ms > 0) has_v2_par = true;
        if (comp.v2_parallel_border_first.elapsed_ms > 0) has_v2_par_bf = true;
    }

    // Calculate table width based on active columns
    int num_solver_cols = (has_v0 ? 1 : 0) + (has_v1 ? 1 : 0) + (has_v1_par ? 1 : 0) + (has_v2_std ? 1 : 0) + (has_v2_bf ? 1 : 0) +
                          (has_v2_par ? 1 : 0) + (has_v2_par_bf ? 1 : 0);
    int table_width = 36 + (num_solver_cols * 15);  // puzzle + size + (time+solved per solver)

    // Header
    std::cout << "\n" << std::string(table_width, '=') << std::endl;
    std::cout << "BENCHMARK RESULTS TABLE" << std::endl;
    std::cout << std::string(table_width, '=') << std::endl;

    // Column headers - Row 1 (Solver names)
    std::cout << std::left << std::setw(30) << "Puzzle"
              << std::right << std::setw(6) << "Size";
    if (has_v0) std::cout << std::setw(15) << "V0";
    if (has_v1) std::cout << std::setw(15) << "V1";
    if (has_v1_par) std::cout << std::setw(15) << "V1-Par";
    if (has_v2_std) std::cout << std::setw(15) << "V2-Std";
    if (has_v2_bf) std::cout << std::setw(15) << "V2-BF";
    if (has_v2_par) std::cout << std::setw(15) << "V2-Par";
    if (has_v2_par_bf) std::cout << std::setw(15) << "V2-Par-BF";
    std::cout << std::endl;

    // Column headers - Row 2 (Units)
    std::cout << std::left << std::setw(30) << ""
              << std::right << std::setw(6) << "";
    int cols = (has_v0 ? 1 : 0) + (has_v1 ? 1 : 0) + (has_v1_par ? 1 : 0) + (has_v2_std ? 1 : 0) + (has_v2_bf ? 1 : 0) +
               (has_v2_par ? 1 : 0) + (has_v2_par_bf ? 1 : 0);
    for (int i = 0; i < cols; ++i) {
        std::cout << std::setw(15) << "Time(ms)/Slv";
    }
    std::cout << std::endl;

    std::cout << std::string(table_width, '-') << std::endl;

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

        // Helper lambda to print time and solved status
        auto print_result = [](const BenchmarkResult& result) {
            std::ostringstream oss;
            if (result.elapsed_ms > 0) {
                oss << std::fixed << std::setprecision(1) << result.elapsed_ms;
                oss << "/" << (result.solved ? "Y" : "N");
            } else {
                oss << "-";
            }
            std::cout << std::setw(15) << oss.str();
        };

        if (has_v0) print_result(comp.v0_result);
        if (has_v1) print_result(comp.v1_result);
        if (has_v1_par) print_result(comp.v1_parallel);
        if (has_v2_std) print_result(comp.v2_standard);
        if (has_v2_bf) print_result(comp.v2_border_first);
        if (has_v2_par) print_result(comp.v2_parallel);
        if (has_v2_par_bf) print_result(comp.v2_parallel_border_first);

        std::cout << std::endl;
    }

    std::cout << std::string(table_width, '=') << std::endl;

    // Print speedup summary if V1 and at least one V2 variant exist
    if (has_v1 && (has_v2_std || has_v2_bf || has_v2_par || has_v2_par_bf)) {
        std::cout << "\nSpeedup vs V1 (best V2 variant per puzzle):" << std::endl;
        for (const auto& comp : comparisons) {
            if (!comp.v1_result.solved || comp.v1_result.elapsed_ms == 0) continue;

            const auto& best = comp.best_v2();
            if (!best.solved || best.elapsed_ms == 0) continue;

            double speedup = comp.v1_result.elapsed_ms / best.elapsed_ms;

            std::string filename = comp.puzzle_file;
            size_t pos = filename.find_last_of("/\\");
            if (pos != std::string::npos) {
                filename = filename.substr(pos + 1);
            }

            std::cout << "  " << std::left << std::setw(40) << filename
                      << std::right << std::fixed << std::setprecision(2)
                      << std::setw(6) << speedup << "x"
                      << "  (" << best.solver_name << ")" << std::endl;
        }
    }
}

void Benchmark::print_summary(const BenchmarkSummary& summary) {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "BENCHMARK SUMMARY" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    std::cout << "\nPuzzles tested: " << summary.total_puzzles << std::endl;

    std::cout << "\n--- Solve Rates ---" << std::endl;
    if (summary.v0_solved > 0)
        std::cout << "V0:               " << summary.v0_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v1_solved > 0)
        std::cout << "V1:               " << summary.v1_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v1_par_solved > 0)
        std::cout << "V1-Par:           " << summary.v1_par_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v2_std_solved > 0)
        std::cout << "V2-Std:           " << summary.v2_std_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v2_bf_solved > 0)
        std::cout << "V2-BF:            " << summary.v2_bf_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v2_par_solved > 0)
        std::cout << "V2-Par:           " << summary.v2_par_solved << "/" << summary.total_puzzles << std::endl;
    if (summary.v2_par_bf_solved > 0)
        std::cout << "V2-Par-BF:        " << summary.v2_par_bf_solved << "/" << summary.total_puzzles << std::endl;

    std::cout << "\n--- Average Times ---" << std::endl;
    if (summary.avg_v0_time_ms > 0)
        std::cout << "V0:               " << std::fixed << std::setprecision(2)
                  << summary.avg_v0_time_ms << " ms" << std::endl;
    if (summary.avg_v1_time_ms > 0)
        std::cout << "V1:               " << std::fixed << std::setprecision(2)
                  << summary.avg_v1_time_ms << " ms" << std::endl;
    if (summary.avg_v1_par_time_ms > 0)
        std::cout << "V1-Par:           " << std::fixed << std::setprecision(2)
                  << summary.avg_v1_par_time_ms << " ms" << std::endl;
    if (summary.avg_v2_std_time_ms > 0)
        std::cout << "V2-Std:           " << std::fixed << std::setprecision(2)
                  << summary.avg_v2_std_time_ms << " ms" << std::endl;
    if (summary.avg_v2_bf_time_ms > 0)
        std::cout << "V2-BF:            " << std::fixed << std::setprecision(2)
                  << summary.avg_v2_bf_time_ms << " ms" << std::endl;
    if (summary.avg_v2_par_time_ms > 0)
        std::cout << "V2-Par:           " << std::fixed << std::setprecision(2)
                  << summary.avg_v2_par_time_ms << " ms" << std::endl;
    if (summary.avg_v2_par_bf_time_ms > 0)
        std::cout << "V2-Par-BF:        " << std::fixed << std::setprecision(2)
                  << summary.avg_v2_par_bf_time_ms << " ms" << std::endl;

    if (summary.max_speedup > 0) {
        std::cout << "\n--- Speedup (Best V2 vs V1) ---" << std::endl;
        std::cout << "Average speedup:  " << std::fixed << std::setprecision(2)
                  << summary.avg_best_speedup << "x" << std::endl;
        std::cout << "Max speedup:      " << std::fixed << std::setprecision(2)
                  << summary.max_speedup << "x (" << summary.max_speedup_puzzle << ")" << std::endl;
        std::cout << "Min speedup:      " << std::fixed << std::setprecision(2)
                  << summary.min_speedup << "x (" << summary.min_speedup_puzzle << ")" << std::endl;
        if (!summary.best_variant_name.empty()) {
            std::cout << "Most often best:  " << summary.best_variant_name << std::endl;
        }
    }

    std::cout << std::string(60, '=') << std::endl;
}

std::string Benchmark::to_csv(const std::vector<BenchmarkComparison>& comparisons) {
    std::ostringstream csv;

    // Header
    csv << "puzzle_file,board_size,"
        << "v1_solved,v1_time_ms,v1_nodes,v1_hash_hits,"
        << "v2_std_solved,v2_std_time_ms,v2_std_nodes,v2_std_backtracks,v2_std_domain_wipeouts,"
        << "v2_bf_solved,v2_bf_time_ms,v2_bf_nodes,v2_bf_backtracks,v2_bf_domain_wipeouts,"
        << "v2_par_solved,v2_par_time_ms,v2_par_nodes,v2_par_backtracks,v2_par_domain_wipeouts,"
        << "v2_par_bf_solved,v2_par_bf_time_ms,v2_par_bf_nodes,v2_par_bf_backtracks,v2_par_bf_domain_wipeouts,"
        << "best_v2_variant,best_v2_time_ms,speedup_vs_v1\n";

    // Data
    for (const auto& comp : comparisons) {
        csv << "\"" << comp.puzzle_file << "\","
            << comp.board_size << ",";

        // V1 results
        csv << (comp.v1_result.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v1_result.elapsed_ms << ","
            << comp.v1_result.nodes_explored << ","
            << comp.v1_result.hash_hits << ",";

        // V2 Standard results
        csv << (comp.v2_standard.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v2_standard.elapsed_ms << ","
            << comp.v2_standard.nodes_explored << ","
            << comp.v2_standard.backtracks << ","
            << comp.v2_standard.domain_wipeouts << ",";

        // V2 Border-First results
        csv << (comp.v2_border_first.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v2_border_first.elapsed_ms << ","
            << comp.v2_border_first.nodes_explored << ","
            << comp.v2_border_first.backtracks << ","
            << comp.v2_border_first.domain_wipeouts << ",";

        // V2 Parallel results
        csv << (comp.v2_parallel.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v2_parallel.elapsed_ms << ","
            << comp.v2_parallel.nodes_explored << ","
            << comp.v2_parallel.backtracks << ","
            << comp.v2_parallel.domain_wipeouts << ",";

        // V2 Parallel Border-First results
        csv << (comp.v2_parallel_border_first.solved ? "true" : "false") << ","
            << std::fixed << std::setprecision(4) << comp.v2_parallel_border_first.elapsed_ms << ","
            << comp.v2_parallel_border_first.nodes_explored << ","
            << comp.v2_parallel_border_first.backtracks << ","
            << comp.v2_parallel_border_first.domain_wipeouts << ",";

        // Best V2 variant
        const auto& best = comp.best_v2();
        csv << "\"" << best.solver_name << "\","
            << std::fixed << std::setprecision(4) << best.elapsed_ms << ",";

        // Speedup vs V1
        if (comp.v1_result.solved && best.solved && comp.v1_result.elapsed_ms > 0 && best.elapsed_ms > 0) {
            csv << std::fixed << std::setprecision(4) << (comp.v1_result.elapsed_ms / best.elapsed_ms);
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

    // Export the solution with BUCAS URL
    std::string solution_csv = export_board_to_csv_string(result.solution_board.value(), puzzle_name);

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
        if (comp.v2_standard.solved && comp.v2_standard.solution_board.has_value()) {
            export_solution(comp.v2_standard, output_dir + "/v2_standard");
        }
        if (comp.v2_border_first.solved && comp.v2_border_first.solution_board.has_value()) {
            export_solution(comp.v2_border_first, output_dir + "/v2_border_first");
        }
        if (comp.v2_parallel.solved && comp.v2_parallel.solution_board.has_value()) {
            export_solution(comp.v2_parallel, output_dir + "/v2_parallel");
        }
        if (comp.v2_parallel_border_first.solved && comp.v2_parallel_border_first.solution_board.has_value()) {
            export_solution(comp.v2_parallel_border_first, output_dir + "/v2_parallel_border_first");
        }
    }
    
    std::cout << "All solutions exported to: " << output_dir << std::endl;
}

} // namespace eternity2_benchmark
