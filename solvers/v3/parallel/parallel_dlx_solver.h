//
// Parallel DLX Solver for Eternity II
// Uses Multi-Level Partitioning with work stealing
//

#ifndef ETERNITY2_V3_PARALLEL_DLX_SOLVER_H
#define ETERNITY2_V3_PARALLEL_DLX_SOLVER_H

#include "../solver/dlx_solver.h"
#include "../config/solver_config.h"
#include "../dlx/dlx_node.h"
#include "common/types.h"
#include "v1/board/board.h"

#include <thread>
#include <vector>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <chrono>

namespace eternity2_v3 {

using namespace eternity2_common;

// Per-thread statistics
struct ThreadStats {
    size_t nodes_explored = 0;
    size_t backtracks = 0;
    size_t edge_incompatible = 0;
    size_t max_depth = 0;
};

// Work unit representing a partial solution at partition depth
struct WorkUnit {
    Board partial_board;      // Board state at partition depth
    size_t depth;             // Current search depth (pieces placed)
    HeuristicProfile profile; // Assigned heuristic profile for portfolio search

    WorkUnit() : depth(0), profile(HeuristicProfile::BORDER_FIRST_LCV) {}

    // Move semantics
    WorkUnit(WorkUnit&& other) noexcept
        : partial_board(std::move(other.partial_board))
        , depth(other.depth)
        , profile(other.profile) {}

    WorkUnit& operator=(WorkUnit&& other) noexcept {
        partial_board = std::move(other.partial_board);
        depth = other.depth;
        profile = other.profile;
        return *this;
    }

    // No copy
    WorkUnit(const WorkUnit&) = delete;
    WorkUnit& operator=(const WorkUnit&) = delete;
};

// Thread-safe work queue
class WorkQueue {
public:
    void push(WorkUnit unit);
    bool pop(WorkUnit& unit);
    void finish();
    void abort();
    size_t size() const;

private:
    std::queue<WorkUnit> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> done_{false};
    std::atomic<bool> aborted_{false};
};

// Parallel DLX solver
class ParallelDLXSolver {
public:
    ParallelDLXSolver(const std::vector<Piece>& pieces,
                      size_t board_size,
                      SharedData& shared_data);

    // Solve the puzzle using multiple threads
    SolveResult solve();

    // Get number of threads
    size_t get_num_threads() const { return num_threads_; }

    // Set partition depth (0 = auto-detect)
    void set_partition_depth(size_t depth) { partition_depth_ = depth; }

private:
    std::vector<Piece> pieces_;
    size_t board_size_;
    SharedData& shared_data_;
    size_t num_threads_;
    size_t partition_depth_ = 0;

    // Solution found flag
    std::atomic<bool> solution_found_{false};

    // Per-thread stats
    std::vector<ThreadStats> thread_stats_;

    // Work queue
    WorkQueue work_queue_;

    // Timing
    std::chrono::steady_clock::time_point start_time_;

    // Shared row metadata (built once, shared with all worker threads)
    std::vector<RowMetadata> shared_row_metadata_;

    // Phase 1: Collect work units at partition depth
    void collect_work_units(std::vector<WorkUnit>& units, size_t target_depth);

    // Recursive helper for collecting work units
    void collect_recursive(DLXSolver& solver,
                           Board& board,
                           size_t depth,
                           size_t target_depth,
                           std::vector<WorkUnit>& units,
                           size_t target_units);

    // Calculate optimal partition depth
    size_t calculate_partition_depth() const;

    // Phase 2: Distribute and solve work units
    SolveResult distribute_and_solve(std::vector<WorkUnit>& units);

    // Worker thread function
    void worker_thread(size_t thread_id);

    // Check if limits reached
    bool limits_reached() const;
};

} // namespace eternity2_v3

#endif // ETERNITY2_V3_PARALLEL_DLX_SOLVER_H
