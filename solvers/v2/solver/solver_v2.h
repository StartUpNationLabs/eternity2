//
// Optimized Eternity II Solver v2
// Features: MAC (Arc Consistency), MRV, LCV, Degree Heuristic
//

#ifndef ETERNITY2_SOLVER_V2_H
#define ETERNITY2_SOLVER_V2_H

#include "../constraints/domain.h"
#include "../heuristics/variable_ordering.h"
#include "../heuristics/value_ordering.h"
#include "v1/board/board.h"
#include "common/types.h"
#include "common/piece_utils.h"

#include <atomic>
#include <functional>
#include <chrono>
#include <mutex>

namespace eternity2_v2 {

// Heuristic profiles for portfolio parallel search
enum class HeuristicProfile {
    MRV_LCV,           // Current best: MRV + Degree + LCV
    MRV_RANDOM,        // MRV + Degree + Random value ordering
    MRV_ONLY_LCV,      // MRV only (no degree) + LCV
    STATIC_LCV,        // Static ordering + LCV
    MRV_REVERSE_LCV,   // MRV + Degree + Reverse LCV (most constraining first)
    STATIC_RANDOM,     // Static ordering + Random
    COUNT              // Number of profiles
};

// Solve strategy for search ordering
enum class SolveStrategy {
    STANDARD,        // Standard MRV-based search
    BORDER_FIRST    // Two-phase: solve border (corners + edges) first, then interior
};

// Configuration for solver_v2
struct SolverConfig {
    // Heuristic options
    bool use_mrv = true;           // Use MRV variable ordering
    bool use_degree = true;        // Use degree as tie-breaker for MRV
    bool use_lcv = true;           // Use LCV value ordering
    bool use_reverse_lcv = false;  // Use reverse LCV (most constraining first)

    // Search strategy
    SolveStrategy strategy = SolveStrategy::STANDARD;  // Search strategy

    // Statistics and debugging
    bool collect_stats = true;     // Collect detailed statistics
    bool verbose = false;          // Print progress info

    // Limits
    size_t max_backtracks = 0;     // 0 = unlimited
    size_t max_nodes = 0;          // 0 = unlimited
    size_t max_time_ms = 0;        // 0 = unlimited

    // Parallelization options
    size_t num_threads = 1;        // Number of worker threads (1 = single-threaded)
    bool parallel_enabled = false; // Enable parallel search mode
};

// Statistics collected during solving
struct SolverStats {
    std::atomic<size_t> nodes_explored{0};      // Total nodes visited
    std::atomic<size_t> backtracks{0};          // Number of backtracks
    std::atomic<size_t> domain_wipeouts{0};     // Dead ends detected by MAC
    std::atomic<size_t> solutions_found{0};     // Solutions found (usually 1)
    std::atomic<size_t> max_depth{0};           // Maximum search depth reached
    std::atomic<long long> elapsed_ms{0};       // Time elapsed in milliseconds

    // For progress tracking
    std::atomic<size_t> pieces_placed{0};       // Current pieces placed
    std::atomic<size_t> best_depth{0};          // Best depth achieved so far

    void reset() {
        nodes_explored = 0;
        backtracks = 0;
        domain_wipeouts = 0;
        solutions_found = 0;
        max_depth = 0;
        elapsed_ms = 0;
        pieces_placed = 0;
        best_depth = 0;
    }
};

// Shared data for solver (compatible with v1 callbacks)
struct SharedDataV2 {
    Board& max_board;                           // Best board found so far
    std::atomic<long long> max_count{0};        // Max pieces placed
    std::mutex& mutex;                          // Mutex for shared access

    // Control
    std::atomic<bool> stop{false};              // Stop signal

    // Callbacks
    std::function<void(const Board&)> on_board_update = [](const Board&) {};
    std::function<void(const SolverStats&)> on_stats_update = [](const SolverStats&) {};

    // Statistics
    SolverStats stats;

    // Config
    SolverConfig config;
};

// Result of solving
enum class SolveResult {
    SOLVED,         // Solution found
    NO_SOLUTION,    // Proved no solution exists
    STOPPED,        // Stopped by user
    TIMEOUT,        // Time limit reached
    LIMIT_REACHED   // Backtrack or node limit reached
};

// Convert result to string
const char* solve_result_to_string(SolveResult result);

// Create config from heuristic profile
SolverConfig config_from_profile(HeuristicProfile profile);

// Main solver class
class SolverV2 {
public:
    SolverV2(const std::vector<Piece>& pieces, size_t board_size, SharedDataV2& shared_data);

    // Solve the puzzle
    SolveResult solve();

    // Solve from initial state (for parallel work units)
    SolveResult solve_from_state(const Board& initial_board,
                                  const DomainManager& initial_domain,
                                  size_t initial_depth);

    // Get the solution board (valid only if solve() returned SOLVED)
    const Board& get_solution() const { return board_; }

    // Get statistics
    const SolverStats& get_stats() const { return shared_data_.stats; }

private:
    std::vector<Piece> pieces_;
    size_t board_size_;
    Board board_;
    DomainManager domain_manager_;
    SharedDataV2& shared_data_;

    std::chrono::steady_clock::time_point start_time_;

    // Recursive backtracking search
    bool search(size_t depth);

    // Check if limits have been reached
    bool limits_reached() const;

    // Update best board if current is better
    void update_best_board(size_t depth);

    // Select next variable based on config
    VariableSelection select_next_variable();

    // Order values based on config
    std::vector<RotatedPiece> order_values(Index index, const std::vector<RotatedPiece>& values);

    // Final verification of complete solution
    bool verify_solution(const Board& board) const;
};

// Convenience function to solve (mimics v1 interface)
void solve_board_v2(Board& board, const std::vector<Piece>& pieces, SharedDataV2& shared_data);

} // namespace eternity2_v2

#endif // ETERNITY2_SOLVER_V2_H
