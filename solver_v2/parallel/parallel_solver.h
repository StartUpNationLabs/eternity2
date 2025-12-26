//
// Parallel Eternity II Solver v2
// Uses Embarrassingly Parallel Search (EPS) with std::thread
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

namespace eternity2_v2 {

// Per-thread statistics (collected locally, merged at end)
struct ThreadStats {
    size_t nodes_explored = 0;
    size_t backtracks = 0;
    size_t domain_wipeouts = 0;
    size_t max_depth = 0;
};

// Parallel solver using Embarrassingly Parallel Search
class ParallelSolverV2 {
public:
    ParallelSolverV2(const std::vector<Piece>& pieces,
                     size_t board_size,
                     SharedDataV2& shared_data);

    // Solve the puzzle using multiple threads
    SolveResult solve();

    // Get the number of threads that will be used
    size_t get_num_threads() const { return num_threads_; }

private:
    std::vector<Piece> pieces_;
    size_t board_size_;
    SharedDataV2& shared_data_;
    size_t num_threads_;

    // Atomic flag for solution found
    std::atomic<bool> solution_found_{false};

    // Per-thread stats (indexed by thread_id)
    std::vector<ThreadStats> thread_stats_;

    // Worker thread function
    // Each thread handles a subset of first-move choices
    void worker_thread(size_t thread_id,
                       Index first_position,
                       const std::vector<RotatedPiece>& initial_choices,
                       size_t start_idx,
                       size_t end_idx);

    // Recursive search function (called by worker threads)
    // Returns true if solution found
    bool search_recursive(Board& board,
                          DomainManager& domain_manager,
                          size_t depth,
                          ThreadStats& stats);

    // Select next variable using MRV heuristic
    VariableSelection select_next_variable(const DomainManager& domain_manager);

    // Order values using LCV heuristic
    std::vector<RotatedPiece> order_values(DomainManager& domain_manager,
                                           Index index,
                                           const std::vector<RotatedPiece>& values);

    // Check if limits have been reached
    bool limits_reached() const;
};

} // namespace eternity2_v2

#endif // ETERNITY2_V2_PARALLEL_SOLVER_H
