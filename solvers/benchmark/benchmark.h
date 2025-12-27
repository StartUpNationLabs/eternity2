#ifndef BENCHMARK_H
#define BENCHMARK_H

#include <string>
#include <vector>
#include <chrono>
#include <functional>
#include <optional>

// Include Board definition (needed for std::optional<Board>)
#include "v1/board/board.h"

namespace eternity2_benchmark {

// Result of a single benchmark run
struct BenchmarkResult {
    std::string solver_name;
    std::string puzzle_file;
    size_t board_size = 0;

    // Timing
    double elapsed_ms = 0.0;

    // Solution status
    bool solved = false;
    size_t pieces_placed = 0;

    // Solution board (if solved)
    std::optional<Board> solution_board;

    // Search statistics
    size_t nodes_explored = 0;
    size_t backtracks = 0;
    size_t hash_hits = 0;           // V1 only
    size_t domain_wipeouts = 0;     // V2 only

    // Derived metrics
    double nodes_per_ms() const {
        return elapsed_ms > 0 ? nodes_explored / elapsed_ms : 0;
    }

    double backtrack_ratio() const {
        return nodes_explored > 0 ? static_cast<double>(backtracks) / nodes_explored : 0;
    }
};

// Comparison between all solver variants on same puzzle
struct BenchmarkComparison {
    std::string puzzle_file;
    size_t board_size;

    BenchmarkResult v0_result;                // V0 (original simple backtracking)
    BenchmarkResult v1_result;                // V1 (optimized backtracking)
    BenchmarkResult v1_parallel;              // V1 parallel (multi-threaded)
    BenchmarkResult v2_standard;              // V2 with standard strategy
    BenchmarkResult v2_border_first;          // V2 with border-first strategy
    BenchmarkResult v2_parallel;              // V2 parallel with standard strategy
    BenchmarkResult v2_parallel_border_first; // V2 parallel with border-first strategy

    // Speedup metrics - V2 standard vs V1
    double speedup() const {
        if (v2_standard.elapsed_ms <= 0) return 0;
        return v1_result.elapsed_ms / v2_standard.elapsed_ms;
    }

    double node_reduction() const {
        if (v2_standard.nodes_explored == 0) return 0;
        return static_cast<double>(v1_result.nodes_explored) / v2_standard.nodes_explored;
    }

    // V2 parallel speedup (vs V2 single-threaded standard)
    double parallel_speedup() const {
        if (v2_parallel.elapsed_ms <= 0) return 0;
        return v2_standard.elapsed_ms / v2_parallel.elapsed_ms;
    }

    // V2 parallel speedup (vs V1)
    double parallel_vs_v1_speedup() const {
        if (v2_parallel.elapsed_ms <= 0) return 0;
        return v1_result.elapsed_ms / v2_parallel.elapsed_ms;
    }

    // Border-first speedup (vs standard)
    double border_first_speedup() const {
        if (v2_border_first.elapsed_ms <= 0) return 0;
        return v2_standard.elapsed_ms / v2_border_first.elapsed_ms;
    }

    // Best V2 result (fastest time among all V2 variants)
    const BenchmarkResult& best_v2() const {
        const BenchmarkResult* best = &v2_standard;

        if (v2_border_first.solved && v2_border_first.elapsed_ms > 0 &&
            (best->elapsed_ms == 0 || v2_border_first.elapsed_ms < best->elapsed_ms)) {
            best = &v2_border_first;
        }
        if (v2_parallel.solved && v2_parallel.elapsed_ms > 0 &&
            (best->elapsed_ms == 0 || v2_parallel.elapsed_ms < best->elapsed_ms)) {
            best = &v2_parallel;
        }
        if (v2_parallel_border_first.solved && v2_parallel_border_first.elapsed_ms > 0 &&
            (best->elapsed_ms == 0 || v2_parallel_border_first.elapsed_ms < best->elapsed_ms)) {
            best = &v2_parallel_border_first;
        }

        return *best;
    }
};

// Configuration for benchmark runs
struct BenchmarkConfig {
    // Time limits
    size_t timeout_ms = 60000;          // 60 seconds default

    // Multiple runs for averaging
    size_t num_runs = 1;

    // Solver selection - by default all are enabled
    bool run_v0 = true;                          // Run V0 solver (original simple backtracking)
    bool run_v1 = true;                          // Run V1 solver (optimized backtracking)
    bool run_v1_parallel = true;                 // Run V1 parallel (multi-threaded)
    bool run_v2_standard = true;                 // Run V2 with standard strategy
    bool run_v2_border_first = true;             // Run V2 with border-first strategy
    bool run_v2_parallel = true;                 // Run V2 parallel with standard strategy
    bool run_v2_parallel_border_first = true;    // Run V2 parallel with border-first strategy

    // V2 heuristic configuration (applies to all V2 variants)
    bool v2_use_mrv = true;
    bool v2_use_degree = true;
    bool v2_use_lcv = true;

    // V2 parallel configuration
    size_t v2_num_threads = 0;          // 0 = auto-detect

    // V1 configuration
    size_t v1_thread_count = 1;         // Single thread
    size_t v1_parallel_thread_count = 0; // 0 = auto-detect (hardware_concurrency)

    // Execution options
    bool parallel = true;               // Run puzzles in parallel

    // Output options
    bool verbose = false;
    bool show_progress = true;
    bool export_solutions = false;      // Export solved boards to files
    std::string solution_output_dir = "solutions";  // Directory for exported solutions

    // Legacy compatibility - kept for now, deprecated
    bool run_v2 = true;                 // Deprecated: use run_v2_standard instead
    bool v2_border_first = false;       // Deprecated: use run_v2_border_first instead
};

// Aggregate statistics across multiple puzzles
struct BenchmarkSummary {
    size_t total_puzzles = 0;
    size_t v0_solved = 0;
    size_t v1_solved = 0;
    size_t v1_par_solved = 0;
    size_t v2_std_solved = 0;
    size_t v2_bf_solved = 0;
    size_t v2_par_solved = 0;
    size_t v2_par_bf_solved = 0;

    // Average times
    double avg_v0_time_ms = 0.0;
    double avg_v1_time_ms = 0.0;
    double avg_v1_par_time_ms = 0.0;
    double avg_v2_std_time_ms = 0.0;
    double avg_v2_bf_time_ms = 0.0;
    double avg_v2_par_time_ms = 0.0;
    double avg_v2_par_bf_time_ms = 0.0;

    // Best V2 variant per puzzle (average speedup vs V1)
    double avg_best_speedup = 0.0;
    double max_speedup = 0.0;
    double min_speedup = std::numeric_limits<double>::max();
    std::string max_speedup_puzzle;
    std::string min_speedup_puzzle;
    std::string best_variant_name;  // Most common best variant

    // Legacy fields for backwards compatibility
    size_t v2_solved = 0;  // Will be set to v2_std_solved
    double avg_v2_time_ms = 0.0;
    double avg_speedup = 0.0;
    double avg_node_reduction = 0.0;
    size_t total_v1_nodes = 0;
    size_t total_v2_nodes = 0;
    size_t total_v1_backtracks = 0;
    size_t total_v2_backtracks = 0;
};

// Main benchmark runner class
class Benchmark {
public:
    Benchmark(const BenchmarkConfig& config = BenchmarkConfig());

    // Run benchmark on a single puzzle
    BenchmarkComparison run_comparison(const std::string& puzzle_file);

    // Run benchmark on multiple puzzles
    std::vector<BenchmarkComparison> run_all(const std::vector<std::string>& puzzle_files);

    // Generate summary from results
    static BenchmarkSummary summarize(const std::vector<BenchmarkComparison>& results);

    // Output formatters
    static void print_result(const BenchmarkResult& result);
    static void print_comparison(const BenchmarkComparison& comparison);
    static void print_summary(const BenchmarkSummary& summary);
    static void print_table(const std::vector<BenchmarkComparison>& comparisons);

    // CSV export
    static std::string to_csv(const std::vector<BenchmarkComparison>& comparisons);
    static void export_csv(const std::vector<BenchmarkComparison>& comparisons,
                          const std::string& output_file);
    
    // Solution export
    static void export_solution(const BenchmarkResult& result, const std::string& output_dir);
    static void export_all_solutions(const std::vector<BenchmarkComparison>& comparisons,
                                    const std::string& output_dir);

private:
    BenchmarkConfig config_;

    // Individual solver runners
    BenchmarkResult run_v0(const std::string& puzzle_file);
    BenchmarkResult run_v1(const std::string& puzzle_file);
    BenchmarkResult run_v1_parallel(const std::string& puzzle_file);
    BenchmarkResult run_v2(const std::string& puzzle_file, bool border_first = false);
    BenchmarkResult run_v2_parallel(const std::string& puzzle_file, bool border_first = false);
};

} // namespace eternity2_benchmark

#endif // BENCHMARK_H
