//
// Solver V3 Configuration
//

#ifndef ETERNITY2_V3_SOLVER_CONFIG_H
#define ETERNITY2_V3_SOLVER_CONFIG_H

#include <cstddef>
#include <string>
#include <atomic>
#include <mutex>
#include <functional>
#include "v1/board/board.h"

namespace eternity2_v3 {

/**
 * @brief Solve result enumeration
 */
enum class SolveResult {
    SOLVED,          // Solution found
    NO_SOLUTION,     // Exhausted search, no solution exists
    TIMEOUT,         // Time limit reached
    STOPPED,         // Manually stopped
    ERROR            // Error during solving
};

/**
 * @brief Convert solve result to string
 */
inline const char* solve_result_to_string(SolveResult result) {
    switch (result) {
        case SolveResult::SOLVED: return "SOLVED";
        case SolveResult::NO_SOLUTION: return "NO_SOLUTION";
        case SolveResult::TIMEOUT: return "TIMEOUT";
        case SolveResult::STOPPED: return "STOPPED";
        case SolveResult::ERROR: return "ERROR";
        default: return "UNKNOWN";
    }
}

/**
 * @brief Heuristic profile for portfolio search
 *
 * Different profiles guide the search in different ways, which is
 * useful for parallel portfolio search where diversity helps.
 */
enum class HeuristicProfile {
    BORDER_FIRST_LCV,      // Border-first column selection + LCV row ordering (default)
    BORDER_FIRST_RANDOM,   // Border-first + random row ordering
    S_HEURISTIC_LCV,       // Pure S-heuristic + LCV
    CORNER_HEAVY,          // Extra corner priority + LCV
    RARE_COLOR_FIRST,      // Prefer pieces with rare colors (reverse LCV)
    REVERSE_LCV,           // Try most constraining values first (diversification)
    COUNT                  // Number of profiles
};

/**
 * @brief Convert heuristic profile to string
 */
inline const char* heuristic_profile_to_string(HeuristicProfile profile) {
    switch (profile) {
        case HeuristicProfile::BORDER_FIRST_LCV: return "BORDER_FIRST_LCV";
        case HeuristicProfile::BORDER_FIRST_RANDOM: return "BORDER_FIRST_RANDOM";
        case HeuristicProfile::S_HEURISTIC_LCV: return "S_HEURISTIC_LCV";
        case HeuristicProfile::CORNER_HEAVY: return "CORNER_HEAVY";
        case HeuristicProfile::RARE_COLOR_FIRST: return "RARE_COLOR_FIRST";
        case HeuristicProfile::REVERSE_LCV: return "REVERSE_LCV";
        default: return "UNKNOWN";
    }
}

/**
 * @brief Solver statistics
 */
struct SolverStats {
    std::atomic<size_t> nodes_explored{0};
    std::atomic<size_t> backtracks{0};
    std::atomic<size_t> edge_incompatible{0};  // Rows skipped due to edge mismatch
    std::atomic<size_t> solutions_found{0};
    std::atomic<size_t> max_depth{0};
    std::atomic<size_t> best_depth{0};

    void reset() {
        nodes_explored = 0;
        backtracks = 0;
        edge_incompatible = 0;
        solutions_found = 0;
        max_depth = 0;
        best_depth = 0;
    }
};

/**
 * @brief Solver configuration
 */
struct SolverConfig {
    // Heuristics
    bool use_s_heuristic = true;       // Column selection by min size (legacy, use heuristic_profile instead)
    bool use_edge_propagation = true;  // Check edge compatibility during search
    HeuristicProfile heuristic_profile = HeuristicProfile::BORDER_FIRST_LCV;  // Column/row selection strategy

    // Randomization
    uint32_t random_seed = 0;           // Random seed (0 = use time-based seed, each thread gets unique seed)
    float randomization_strength = 0.3f; // 0.0 = deterministic, 1.0 = fully random (default: 0.3 = light randomization)

    // Limits
    size_t max_time_ms = 0;            // 0 = unlimited
    size_t max_nodes = 0;              // 0 = unlimited

    // Parallel execution
    bool parallel_enabled = false;
    size_t num_threads = 1;
    size_t partition_depth = 0;        // 0 = auto-calculate
    bool portfolio_enabled = true;     // Use different profiles per work unit

    // Output
    bool verbose = false;
    bool export_partial = false;
    std::string export_dir = ".";
    std::string export_prefix = "partial_solution";

    // Puzzle name for BUCAS URL
    std::string puzzle_name = "puzzle";

    // Hint options
    bool use_hints = true;         // Use pre-placed pieces (hints) from the board if present
};

/**
 * @brief Shared data between solver instances (for parallel mode)
 */
struct SharedData {
    Board max_board;                   // Best board found so far
    std::atomic<long long> max_count{0};  // Best depth reached
    SolverStats stats;
    std::mutex mutex;
    std::atomic<bool> stop{false};
    SolverConfig config;
    std::string puzzle_name;

    // Callback for board updates (progress tracking)
    std::function<void(const Board&)> on_board_update = [](const Board&) {};
};

} // namespace eternity2_v3

#endif // ETERNITY2_V3_SOLVER_CONFIG_H
