//
// Parallel Eternity II Solver v2
// Uses Multi-Level Partitioning + Portfolio Search
//

#ifndef ETERNITY2_V2_PARALLEL_SOLVER_H
#define ETERNITY2_V2_PARALLEL_SOLVER_H

#include "../solver/solver_v2.h"
#include "../constraints/domain.h"
#include "../heuristics/variable_ordering.h"
#include "../heuristics/value_ordering.h"

#include <thread>
#include <vector>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>

namespace eternity2_v2 {

// Per-thread statistics (collected locally, merged at end)
struct ThreadStats {
    size_t nodes_explored = 0;
    size_t backtracks = 0;
    size_t domain_wipeouts = 0;
    size_t max_depth = 0;
};

// Work unit representing a partial solution at partition depth
struct WorkUnit {
    Board partial_board;                          // Board state at partition depth
    std::unique_ptr<DomainManager> partial_domain; // Domain state (unique_ptr for move semantics)
    size_t depth;                                 // Current search depth
    HeuristicProfile profile;                     // Heuristic configuration for this unit

    // Default constructor
    WorkUnit() : depth(0), profile(HeuristicProfile::MRV_LCV) {}

    // Move constructor (needed for queue)
    WorkUnit(WorkUnit&& other) noexcept
        : partial_board(std::move(other.partial_board))
        , partial_domain(std::move(other.partial_domain))
        , depth(other.depth)
        , profile(other.profile) {}

    // Move assignment
    WorkUnit& operator=(WorkUnit&& other) noexcept {
        partial_board = std::move(other.partial_board);
        partial_domain = std::move(other.partial_domain);
        depth = other.depth;
        profile = other.profile;
        return *this;
    }

    // No copy
    WorkUnit(const WorkUnit&) = delete;
    WorkUnit& operator=(const WorkUnit&) = delete;
};

// Thread-safe work queue for distributing work units
class WorkQueue {
public:
    void push(WorkUnit unit);
    bool pop(WorkUnit& unit);  // Returns false when done and queue is empty
    void finish();             // Signal no more work will be added
    size_t size() const;

private:
    std::queue<WorkUnit> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> done_{false};
};

// Parallel solver using Multi-Level Partitioning + Portfolio Search
class ParallelSolverV2 {
public:
    ParallelSolverV2(const std::vector<Piece>& pieces,
                     size_t board_size,
                     SharedDataV2& shared_data);

    // Solve the puzzle using multiple threads
    SolveResult solve();

    // Get the number of threads that will be used
    size_t get_num_threads() const { return num_threads_; }

    // Set partition depth (0 = auto-detect)
    void set_partition_depth(size_t depth) { partition_depth_ = depth; }

private:
    std::vector<Piece> pieces_;
    size_t board_size_;
    SharedDataV2& shared_data_;
    size_t num_threads_;
    size_t partition_depth_ = 0;  // 0 = auto-detect

    // Atomic flag for solution found
    std::atomic<bool> solution_found_{false};

    // Per-thread stats (indexed by thread_id)
    std::vector<ThreadStats> thread_stats_;

    // Work queue for distributing units to threads
    WorkQueue work_queue_;

    // Phase 1: Collect work units at partition depth
    void collect_work_units(std::vector<WorkUnit>& units, size_t target_depth);

    // Recursive helper for collecting work units
    void collect_recursive(Board& board,
                           DomainManager& domain_manager,
                           size_t depth,
                           size_t target_depth,
                           std::vector<WorkUnit>& units);

    // Calculate optimal partition depth based on thread count
    size_t calculate_partition_depth() const;

    // Phase 2: Distribute and solve work units
    SolveResult distribute_and_solve(std::vector<WorkUnit>& units);

    // Worker thread function - processes work units from queue
    void worker_thread(size_t thread_id);

    // Select next variable using MRV heuristic
    VariableSelection select_next_variable(const DomainManager& domain_manager,
                                            const SolverConfig& config);

    // Order values using LCV heuristic
    std::vector<RotatedPiece> order_values(DomainManager& domain_manager,
                                           Index index,
                                           const std::vector<RotatedPiece>& values,
                                           const SolverConfig& config);

    // Check if limits have been reached
    bool limits_reached() const;
};

} // namespace eternity2_v2

#endif // ETERNITY2_V2_PARALLEL_SOLVER_H
