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

// Comparison between V1 and V2 on same puzzle
struct BenchmarkComparison {
    std::string puzzle_file;
    size_t board_size;

    BenchmarkResult v1_result;
    BenchmarkResult v2_result;
    BenchmarkResult v2_parallel_result;  // V2 parallel mode result

    // Speedup metrics (V2 single-threaded vs V1)
    double speedup() const {
        if (v2_result.elapsed_ms <= 0) return 0;
        return v1_result.elapsed_ms / v2_result.elapsed_ms;
    }

    double node_reduction() const {
        if (v2_result.nodes_explored == 0) return 0;
        return static_cast<double>(v1_result.nodes_explored) / v2_result.nodes_explored;
    }

    // V2 parallel speedup (vs V2 single-threaded)
    double parallel_speedup() const {
        if (v2_parallel_result.elapsed_ms <= 0) return 0;
        return v2_result.elapsed_ms / v2_parallel_result.elapsed_ms;
    }

    // V2 parallel speedup (vs V1)
    double parallel_vs_v1_speedup() const {
        if (v2_parallel_result.elapsed_ms <= 0) return 0;
        return v1_result.elapsed_ms / v2_parallel_result.elapsed_ms;
    }
};

// Configuration for benchmark runs
struct BenchmarkConfig {
    // Time limits
    size_t timeout_ms = 60000;          // 60 seconds default

    // Multiple runs for averaging
    size_t num_runs = 1;

    // Solver selection
    bool run_v1 = true;                 // Run V1 solver (can disable for V2-only)
    bool run_v2 = true;                 // Run V2 solver

    // V2 heuristic configuration
    bool v2_use_mrv = true;
    bool v2_use_degree = true;
    bool v2_use_lcv = true;
    bool v2_border_first = false;  // Use border-first strategy

    // V2 parallel configuration
    bool run_v2_parallel = false;       // Run V2 parallel solver
    size_t v2_num_threads = 0;          // 0 = auto-detect

    // V1 configuration
    size_t v1_thread_count = 1;         // Single thread for fair comparison

    // Execution options
    bool parallel = true;               // Run puzzles in parallel

    // Output options
    bool verbose = false;
    bool show_progress = true;
    bool export_solutions = false;      // Export solved boards to files
    std::string solution_output_dir = "solutions";  // Directory for exported solutions
};

// Aggregate statistics across multiple puzzles
struct BenchmarkSummary {
    size_t total_puzzles;
    size_t v1_solved;
    size_t v2_solved;

    // Average metrics (for puzzles both solved)
    double avg_v1_time_ms;
    double avg_v2_time_ms;
    double avg_speedup;
    double avg_node_reduction;

    // Best/worst cases
    double max_speedup;
    double min_speedup;
    std::string max_speedup_puzzle;
    std::string min_speedup_puzzle;

    // Totals
    size_t total_v1_nodes;
    size_t total_v2_nodes;
    size_t total_v1_backtracks;
    size_t total_v2_backtracks;
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
    BenchmarkResult run_v1(const std::string& puzzle_file);
    BenchmarkResult run_v2(const std::string& puzzle_file);
    BenchmarkResult run_v2_parallel(const std::string& puzzle_file);
};

} // namespace eternity2_benchmark

#endif // BENCHMARK_H
