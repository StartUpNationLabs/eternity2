//
// Parallel Eternity II Solver v2 Implementation
// Uses Multi-Level Partitioning + Portfolio Search
//

#include "parallel_solver.h"
#include "v1/board/board.h"
#include "common/types.h"
#include "common/piece_utils.h"
#include <iostream>
#include <algorithm>
#include <chrono>
#include <thread>

using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::get_piece_part;

namespace eternity2_v2 {

// ============================================================================
// WorkQueue Implementation
// ============================================================================

void WorkQueue::push(WorkUnit unit) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(unit));
    }
    cv_.notify_one();
}

bool WorkQueue::pop(WorkUnit& unit) {
    std::unique_lock<std::mutex> lock(mutex_);

    // Wait until there's work, we're done, or aborted
    cv_.wait(lock, [this] {
        return !queue_.empty() || done_ || aborted_;
    });

    // Check abort first - exit immediately if solution found
    if (aborted_) {
        return false;
    }

    if (queue_.empty()) {
        return false;  // No more work
    }

    unit = std::move(queue_.front());
    queue_.pop();
    return true;
}

void WorkQueue::finish() {
    done_ = true;
    cv_.notify_all();
}

void WorkQueue::abort() {
    aborted_ = true;
    cv_.notify_all();  // Wake up all waiting threads
}

size_t WorkQueue::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.size();
}

// ============================================================================
// ParallelSolverV2 Implementation
// ============================================================================

ParallelSolverV2::ParallelSolverV2(const std::vector<Piece>& pieces,
                                   size_t board_size,
                                   SharedDataV2& shared_data)
    : pieces_(pieces)
    , board_size_(board_size)
    , shared_data_(shared_data)
{
    // Determine number of threads
    num_threads_ = shared_data_.config.num_threads;
    if (num_threads_ == 0) {
        num_threads_ = std::thread::hardware_concurrency();
        if (num_threads_ == 0) {
            num_threads_ = 4;  // Fallback
        }
    }
}

SolveResult ParallelSolverV2::solve() {
    auto start_time = std::chrono::steady_clock::now();

    // Set global start time for timeout checks across all worker threads
    shared_data_.global_start_time = start_time;

    // Calculate partition depth (or use provided value)
    size_t target_depth = (partition_depth_ > 0) ? partition_depth_ : calculate_partition_depth();

    if (shared_data_.config.verbose) {
        std::cout << "Parallel solver: " << num_threads_ << " threads, partition depth " << target_depth << std::endl;
    }

    // Phase 1: Collect work units at partition depth (SERIAL - this is the bottleneck!)
    auto collect_start = std::chrono::steady_clock::now();
    std::vector<WorkUnit> work_units;
    collect_work_units(work_units, target_depth);
    auto collect_end = std::chrono::steady_clock::now();
    auto collect_ms = std::chrono::duration_cast<std::chrono::milliseconds>(collect_end - collect_start).count();

    if (work_units.empty()) {
        // No valid work units found (puzzle unsolvable from start)
        return SolveResult::NO_SOLUTION;
    }

    if (shared_data_.config.verbose) {
        std::cout << "Collected " << work_units.size() << " work units in " << collect_ms << " ms (serial phase)" << std::endl;
    }

    // Phase 2: Distribute and solve
    SolveResult result = distribute_and_solve(work_units);

    // Update elapsed time
    auto end_time = std::chrono::steady_clock::now();
    shared_data_.stats.elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time).count();

    return result;
}

size_t ParallelSolverV2::calculate_partition_depth() const {
    // Target: ~4-8x more work units than threads for good load balancing
    //
    // With BORDER-FIRST strategy, the search tree is much narrower at shallow depths:
    // - Depth 0-1: Only 4 corners with ~3 rotations each = ~12 branches
    // - Need deeper partition to get enough work units
    //
    // With STANDARD strategy, branching is wider:
    // - Each position has more choices initially

    bool is_border_first = (shared_data_.config.strategy == SolveStrategy::BORDER_FIRST);

    if (is_border_first) {
        // Border-first needs deeper partitioning due to narrow initial tree
        // Depth 4-5 gives ~50-200 work units (corners + adjacent edges)
        if (num_threads_ <= 4) {
            return 4;
        } else if (num_threads_ <= 8) {
            return 5;
        } else {
            return 6;
        }
    } else {
        // Standard MRV strategy has wider branching
        if (num_threads_ <= 4) {
            return 2;
        } else if (num_threads_ <= 8) {
            return 3;
        } else {
            return 3;
        }
    }
}

void ParallelSolverV2::collect_work_units(std::vector<WorkUnit>& units, size_t target_depth) {
    // Create initial board and domain manager
    Board board = create_board(static_cast<int>(board_size_));
    DomainManager domain_manager(board_size_, pieces_);
    domain_manager.initialize_domains();

    // Collect work units recursively
    collect_recursive(board, domain_manager, 0, target_depth, units);
}

void ParallelSolverV2::collect_recursive(Board& board,
                                          DomainManager& domain_manager,
                                          size_t depth,
                                          size_t target_depth,
                                          std::vector<WorkUnit>& units) {
    // Check for stop signal
    if (shared_data_.stop || solution_found_) {
        return;
    }

    // If we've reached target depth, create a work unit
    if (depth >= target_depth) {
        WorkUnit unit;
        unit.partial_board = board;  // Copy the board
        unit.partial_domain = std::make_unique<DomainManager>(domain_manager);  // Copy domain
        unit.depth = depth;
        unit.profile = HeuristicProfile::MRV_LCV;  // Will be assigned later

        units.push_back(std::move(unit));
        return;
    }

    // Check if complete (shouldn't happen at shallow depths, but check anyway)
    if (domain_manager.is_complete()) {
        // Found solution during collection!
        solution_found_ = true;
        shared_data_.stop = true;
        shared_data_.max_board = board;
        shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
        return;
    }

    // Select next variable - use border-first if configured, otherwise MRV
    SolverConfig config;
    config.use_mrv = true;
    config.use_degree = true;
    config.strategy = shared_data_.config.strategy;  // Copy strategy from main config
    VariableSelection var = select_next_variable(domain_manager, config);

    if (var.is_failure) {
        // Dead end - no work unit to create
        return;
    }

    if (var.domain_size == 0) {
        // No unassigned variables but not complete - shouldn't happen
        return;
    }

    // Get values to try (use random ordering for diversity in work units)
    const DomainEntry& domain = domain_manager.get_domain(var.index);
    std::vector<RotatedPiece> values = order_values_random(domain.valid_pieces);

    // Try each value
    for (const auto& piece : values) {
        if (shared_data_.stop || solution_found_) {
            return;
        }

        // Check if piece is still available
        if (!domain_manager.is_piece_available(piece.index)) {
            continue;
        }

        // Save state for backtracking
        domain_manager.push_state();

        // Place piece on board
        place_piece(board, piece, var.index);

        // Update domain manager
        bool consistent = domain_manager.place_piece(var.index, piece);

        if (consistent) {
            // Recurse to collect more work units
            collect_recursive(board, domain_manager, depth + 1, target_depth, units);
        }

        // Backtrack
        domain_manager.pop_state();
        remove_piece(board, var.index);
    }
}

SolveResult ParallelSolverV2::distribute_and_solve(std::vector<WorkUnit>& units) {
    if (units.empty()) {
        return SolveResult::NO_SOLUTION;
    }

    // Check if solution was found during collection
    if (solution_found_) {
        return SolveResult::SOLVED;
    }

    // Assign heuristic profiles to work units (round-robin for portfolio diversity)
    size_t num_profiles = static_cast<size_t>(HeuristicProfile::COUNT);
    for (size_t i = 0; i < units.size(); ++i) {
        units[i].profile = static_cast<HeuristicProfile>(i % num_profiles);
    }

    // Initialize per-thread stats
    size_t effective_threads = std::min(num_threads_, units.size());
    thread_stats_.resize(effective_threads);
    for (auto& ts : thread_stats_) {
        ts = ThreadStats{};
    }

    // Push all work units to the queue
    for (auto& unit : units) {
        work_queue_.push(std::move(unit));
    }
    work_queue_.finish();  // Signal that all work has been added

    // Launch worker threads
    std::vector<std::thread> threads;
    threads.reserve(effective_threads);

    for (size_t t = 0; t < effective_threads; ++t) {
        threads.emplace_back(&ParallelSolverV2::worker_thread, this, t);
    }

    // Launch progress reporting thread if verbose
    std::thread progress_thread;
    auto parallel_start = std::chrono::steady_clock::now();
    if (shared_data_.config.verbose) {
        progress_thread = std::thread([&, parallel_start]() {
            long long last_count = -1;
            while (!shared_data_.stop && !solution_found_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
                long long current_count = shared_data_.max_count.load();
                if (current_count > last_count) {
                    last_count = current_count;
                    auto now = std::chrono::steady_clock::now();
                    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - parallel_start).count();
                    std::cout << "[" << elapsed_ms << "ms] Progress: " << current_count << "/" << (board_size_ * board_size_)
                              << " pieces placed" << std::endl;
                }
            }
        });
    }

    // Wait for all threads to complete
    for (auto& t : threads) {
        t.join();
    }

    // Wait for progress thread
    if (progress_thread.joinable()) {
        progress_thread.join();
    }

    // Aggregate statistics from all threads
    for (const auto& ts : thread_stats_) {
        shared_data_.stats.nodes_explored += ts.nodes_explored;
        shared_data_.stats.backtracks += ts.backtracks;
        shared_data_.stats.domain_wipeouts += ts.domain_wipeouts;
        if (ts.max_depth > shared_data_.stats.max_depth) {
            shared_data_.stats.max_depth.store(ts.max_depth);
        }
    }

    if (solution_found_) {
        shared_data_.stats.solutions_found++;
        return SolveResult::SOLVED;
    }

    if (shared_data_.stop) {
        return SolveResult::STOPPED;
    }

    if (limits_reached()) {
        return SolveResult::LIMIT_REACHED;
    }

    return SolveResult::NO_SOLUTION;
}

void ParallelSolverV2::worker_thread(size_t thread_id) {
    ThreadStats& stats = thread_stats_[thread_id];

    WorkUnit unit;
    while (work_queue_.pop(unit) && !shared_data_.stop && !solution_found_) {
        // Get config from heuristic profile
        SolverConfig config = config_from_profile(unit.profile);
        // IMPORTANT: Copy strategy from main config (for border-first support)
        config.strategy = shared_data_.config.strategy;

        // Create a temporary SharedDataV2 for this solver instance
        // (shares the stop flag, mutex, max_count, and callbacks but has local config)
        Board local_max_board = create_board(static_cast<int>(board_size_));
        SharedDataV2 local_shared = {
            local_max_board,
            {0},
            shared_data_.mutex  // Share the main mutex
        };
        local_shared.stop.store(shared_data_.stop.load());
        local_shared.config = config;

        // Copy the progress callback from main shared_data and wrap it to update main max_count
        auto original_callback = shared_data_.on_board_update;
        local_shared.on_board_update = [&, original_callback](const Board& board) {
            // Check if global stop was set (solution found by another thread)
            if (shared_data_.stop.load()) {
                local_shared.stop.store(true);
            }

            // Count non-empty pieces on the board
            long long piece_count = 0;
            for (size_t y = 0; y < board_size_; ++y) {
                for (size_t x = 0; x < board_size_; ++x) {
                    Index idx = {x, y};
                    const RotatedPiece* piece = get_piece(board, idx);
                    if (piece->piece != EMPTY && piece->piece != 0) {
                        piece_count++;
                    }
                }
            }

            // Update main shared_data_.max_count if this is better
            {
                std::scoped_lock lock(shared_data_.mutex);
                if (piece_count > shared_data_.max_count.load()) {
                    shared_data_.max_count = piece_count;
                    shared_data_.max_board = board;
                }
            }

            // Call original callback if it exists
            if (original_callback) {
                original_callback(board);
            }
        };

        // Create solver and solve from the work unit's state
        SolverV2 solver(pieces_, board_size_, local_shared);
        SolveResult result = solver.solve_from_state(
            unit.partial_board,
            *unit.partial_domain,
            unit.depth
        );

        // Update local stats
        stats.nodes_explored += local_shared.stats.nodes_explored;
        stats.backtracks += local_shared.stats.backtracks;
        stats.domain_wipeouts += local_shared.stats.domain_wipeouts;
        if (local_shared.stats.max_depth > stats.max_depth) {
            stats.max_depth = local_shared.stats.max_depth;
        }
        
        // Update main shared_data_.max_count if local found a better partial solution
        {
            std::scoped_lock lock(shared_data_.mutex);
            if (local_shared.max_count.load() > shared_data_.max_count.load()) {
                shared_data_.max_count = local_shared.max_count.load();
                shared_data_.max_board = local_shared.max_board;
                // Trigger callback to show progress
                if (shared_data_.on_board_update) {
                    shared_data_.on_board_update(local_shared.max_board);
                }
            }
        }

        if (result == SolveResult::SOLVED) {
            // Solution found! Use compare-exchange to ensure only first thread claims victory
            bool expected = false;
            if (solution_found_.compare_exchange_strong(expected, true)) {
                // We are the first thread to find a solution
                shared_data_.stop = true;

                // CRITICAL: Abort work queue to wake up waiting threads
                work_queue_.abort();

                // Update shared solution (thread-safe with mutex)
                {
                    std::scoped_lock lock(shared_data_.mutex);
                    shared_data_.max_board = solver.get_solution();
                    shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
                }

                if (shared_data_.config.verbose) {
                    std::cout << "Thread " << thread_id << " FOUND SOLUTION with profile "
                              << static_cast<int>(unit.profile) << std::endl;
                }
            }
            break;
        }

        // Check if global stop was triggered by another thread
        if (shared_data_.stop) {
            if (shared_data_.config.verbose) {
                std::cout << "Thread " << thread_id << " stopping (solution found by other thread)" << std::endl;
            }
            break;
        }
    }

    if (shared_data_.config.verbose) {
        std::cout << "Thread " << thread_id << " exiting - "
                  << stats.nodes_explored << " nodes explored" << std::endl;
    }
}

VariableSelection ParallelSolverV2::select_next_variable(const DomainManager& domain_manager,
                                                          const SolverConfig& config) {
    // Check strategy first - border-first overrides MRV settings
    if (config.strategy == SolveStrategy::BORDER_FIRST) {
        return select_variable_border_first(domain_manager);
    }

    // Standard MRV-based selection
    if (config.use_mrv) {
        if (config.use_degree) {
            return select_variable_mrv(domain_manager);
        } else {
            return select_variable_mrv_simple(domain_manager);
        }
    } else {
        return select_variable_static(domain_manager);
    }
}

std::vector<RotatedPiece> ParallelSolverV2::order_values(DomainManager& domain_manager,
                                                          Index index,
                                                          const std::vector<RotatedPiece>& values,
                                                          const SolverConfig& config) {
    if (config.use_lcv) {
        if (config.use_reverse_lcv) {
            // Reverse LCV - most constraining first
            auto ordered = order_values_lcv(domain_manager, index, values);
            std::reverse(ordered.begin(), ordered.end());
            return ordered;
        }
        return order_values_lcv(domain_manager, index, values);
    } else {
        return order_values_random(values);
    }
}

bool ParallelSolverV2::limits_reached() const {
    const auto& config = shared_data_.config;
    const auto& stats = shared_data_.stats;

    if (config.max_backtracks > 0 && stats.backtracks >= config.max_backtracks) {
        return true;
    }

    if (config.max_nodes > 0 && stats.nodes_explored >= config.max_nodes) {
        return true;
    }

    return false;
}

} // namespace eternity2_v2
