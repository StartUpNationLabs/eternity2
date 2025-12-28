//
// Parallel DLX Solver Implementation
//

#include "parallel_dlx_solver.h"
#include "solver/dlx_solver.h"
#include "common/piece_utils.h"
#include <iostream>
#include <algorithm>

namespace eternity2_v3 {

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

    cv_.wait(lock, [this] {
        return !queue_.empty() || done_ || aborted_;
    });

    if (aborted_) {
        return false;
    }

    if (queue_.empty()) {
        return false;
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
    cv_.notify_all();
}

size_t WorkQueue::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.size();
}

// ============================================================================
// ParallelDLXSolver Implementation
// ============================================================================

ParallelDLXSolver::ParallelDLXSolver(const std::vector<Piece>& pieces,
                                     size_t board_size,
                                     SharedData& shared_data)
    : pieces_(pieces)
    , board_size_(board_size)
    , shared_data_(shared_data)
{
    num_threads_ = shared_data_.config.num_threads;
    if (num_threads_ == 0) {
        num_threads_ = std::thread::hardware_concurrency();
        if (num_threads_ == 0) {
            num_threads_ = 4;
        }
    }
}

SolveResult ParallelDLXSolver::solve() {
    start_time_ = std::chrono::steady_clock::now();

    // Calculate partition depth
    size_t target_depth = (partition_depth_ > 0) ? partition_depth_ : calculate_partition_depth();

    if (shared_data_.config.verbose) {
        std::cout << "[INFO] Parallel DLX solver: " << num_threads_ << " threads, partition depth " << target_depth << std::endl;
    }

    // Phase 1: Collect work units
    if (shared_data_.config.verbose) {
        std::cout << "[INFO] === Phase 1: Work Unit Collection ===" << std::endl;
    }
    auto collect_start = std::chrono::steady_clock::now();
    std::vector<WorkUnit> work_units;
    collect_work_units(work_units, target_depth);
    auto collect_end = std::chrono::steady_clock::now();
    auto collect_ms = std::chrono::duration_cast<std::chrono::milliseconds>(collect_end - collect_start).count();

    if (work_units.empty()) {
        if (shared_data_.config.verbose) {
            std::cout << "[INFO] No work units collected - no solution possible" << std::endl;
        }
        return SolveResult::NO_SOLUTION;
    }

    if (shared_data_.config.verbose) {
        std::cout << "[INFO] === Phase 2: Parallel Solving ===" << std::endl;
        std::cout << "[INFO] Distributing " << work_units.size() << " work units to " << num_threads_ << " threads..." << std::endl;
    }

    // Check if solution was found during collection
    if (solution_found_) {
        return SolveResult::SOLVED;
    }

    // Phase 2: Distribute and solve
    return distribute_and_solve(work_units);
}

size_t ParallelDLXSolver::calculate_partition_depth() const {
    // Target: 8-12x more work units than threads for good load balancing
    //
    // For 16x16 puzzles with border-first:
    // - Depth 4: 4 corners placed, ~24 branches (4! permutations reduced by constraints)
    // - Depth 8: corners + some edges, ~100-200 branches
    //
    // For smaller puzzles, branching is narrower
    size_t num_positions = board_size_ * board_size_;
    size_t target_units = num_threads_ * 10;

    // For large puzzles (16x16), use deeper partitioning
    if (num_positions >= 256) {  // 16x16
        if (num_threads_ <= 4) {
            return 5;  // ~100 work units
        } else if (num_threads_ <= 8) {
            return 6;  // ~400 work units
        } else if (num_threads_ <= 16) {
            return 7;  // ~1000 work units
        } else {
            return 8;  // ~2000+ work units
        }
    }

    // For medium puzzles (8x8 to 12x12)
    if (num_positions >= 64) {
        if (num_threads_ <= 4) {
            return 4;
        } else if (num_threads_ <= 8) {
            return 5;
        } else {
            return 6;
        }
    }

    // For small puzzles
    if (num_threads_ <= 4) {
        return 3;
    } else {
        return 4;
    }
}

void ParallelDLXSolver::collect_work_units(std::vector<WorkUnit>& units, size_t target_depth) {
    // Create a solver for collection with its own SharedData
    SharedData collect_shared;
    collect_shared.max_board = create_board(static_cast<int>(board_size_));
    collect_shared.config = shared_data_.config;
    collect_shared.config.verbose = false;  // Quiet during collection

    DLXSolver solver(pieces_, board_size_, collect_shared);

    // Build the matrix
    if (shared_data_.config.verbose) {
        std::cout << "[INFO] Building DLX matrix for work unit collection..." << std::endl;
    }
    auto matrix_start = std::chrono::steady_clock::now();
    solver.matrix_.build_matrix();
    auto matrix_end = std::chrono::steady_clock::now();
    auto matrix_ms = std::chrono::duration_cast<std::chrono::milliseconds>(matrix_end - matrix_start).count();

    // Store the row metadata for sharing with worker threads
    shared_row_metadata_ = solver.matrix_.get_row_metadata_ref();
    
    if (shared_data_.config.verbose) {
        std::cout << "[INFO] Matrix built: " << shared_row_metadata_.size() << " rows in " << matrix_ms << " ms" << std::endl;
        std::cout << "[INFO] Storing row metadata for sharing with " << num_threads_ << " worker threads" << std::endl;
    }

    // Initialize empty board
    Board board = create_board(static_cast<int>(board_size_));

    // Calculate target number of work units (early termination)
    // Collect 3x thread count for good load balancing
    size_t target_units = num_threads_ * 3;
    
    if (shared_data_.config.verbose) {
        std::cout << "[INFO] Collecting work units (target: " << target_units << ", depth: " << target_depth << ")..." << std::endl;
    }

    // Collect recursively with early termination
    auto collect_start = std::chrono::steady_clock::now();
    collect_recursive(solver, board, 0, target_depth, units, target_units);
    auto collect_end = std::chrono::steady_clock::now();
    auto collect_ms = std::chrono::duration_cast<std::chrono::milliseconds>(collect_end - collect_start).count();
    
    if (shared_data_.config.verbose) {
        if (units.size() >= target_units) {
            std::cout << "[INFO] Early termination: collected " << units.size() << " work units (target: " << target_units << ") in " << collect_ms << " ms" << std::endl;
        } else {
            std::cout << "[INFO] Collected " << units.size() << " work units in " << collect_ms << " ms" << std::endl;
        }
    }
}

void ParallelDLXSolver::collect_recursive(DLXSolver& solver,
                                           Board& board,
                                           size_t depth,
                                           size_t target_depth,
                                           std::vector<WorkUnit>& units,
                                           size_t target_units) {
    // Check stop conditions
    if (shared_data_.stop || solution_found_ || limits_reached()) {
        return;
    }

    // Early termination: if we have enough work units, stop collecting
    if (units.size() >= target_units) {
        return;
    }

    // Reached target depth - create work unit
    if (depth >= target_depth) {
        WorkUnit unit;
        unit.partial_board = board;  // Copy the board
        unit.depth = depth;
        units.push_back(std::move(unit));
        return;
    }

    // Check if matrix is empty (solution found during collection)
    if (solver.matrix_.is_empty()) {
        solution_found_ = true;
        shared_data_.stop = true;
        shared_data_.max_board = board;
        shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
        return;
    }

    // Choose column with border-first heuristic for balanced work unit generation
    DLXNode* col = solver.matrix_.choose_column_smart();

    if (col == nullptr || col->size == 0) {
        return;  // Dead end
    }

    // Cover the column
    solver.matrix_.cover(col);

    // Try each row
    for (DLXNode* row = col->down; row != col; row = row->down) {
        if (shared_data_.stop || solution_found_) {
            break;
        }

        // Check early termination before processing this row
        if (units.size() >= target_units) {
            break;
        }

        const RowMetadata& meta = solver.matrix_.get_row_metadata(row);

        // Check edge compatibility
        if (!solver.is_edge_compatible(meta)) {
            continue;
        }

        // Place piece on board
        solver.update_placed_edges(meta);

        // Cover other columns in this row
        for (DLXNode* node = row->right; node != row; node = node->right) {
            solver.matrix_.cover(node->column);
        }

        // Recurse
        collect_recursive(solver, solver.board_, depth + 1, target_depth, units, target_units);

        // Backtrack
        for (DLXNode* node = row->left; node != row; node = node->left) {
            solver.matrix_.uncover(node->column);
        }

        solver.remove_placed_edges(meta);
    }

    // Uncover column
    solver.matrix_.uncover(col);
}

SolveResult ParallelDLXSolver::distribute_and_solve(std::vector<WorkUnit>& units) {
    if (units.empty()) {
        return SolveResult::NO_SOLUTION;
    }

    // Initialize per-thread stats
    size_t effective_threads = std::min(num_threads_, units.size());
    thread_stats_.resize(effective_threads);
    for (auto& ts : thread_stats_) {
        ts = ThreadStats{};
    }

    // Assign heuristic profiles round-robin for portfolio diversity
    if (shared_data_.config.portfolio_enabled) {
        size_t num_profiles = static_cast<size_t>(HeuristicProfile::COUNT);
        for (size_t i = 0; i < units.size(); ++i) {
            units[i].profile = static_cast<HeuristicProfile>(i % num_profiles);
        }

        if (shared_data_.config.verbose) {
            std::cout << "[INFO] Portfolio search enabled with " << num_profiles << " heuristic profiles" << std::endl;
        }
    }

    // Push all work units to queue
    for (auto& unit : units) {
        work_queue_.push(std::move(unit));
    }
    work_queue_.finish();

    // Launch worker threads
    std::vector<std::thread> threads;
    threads.reserve(effective_threads);

    for (size_t t = 0; t < effective_threads; ++t) {
        threads.emplace_back(&ParallelDLXSolver::worker_thread, this, t);
    }

    // Progress reporting thread
    std::thread progress_thread;
    if (shared_data_.config.verbose) {
        progress_thread = std::thread([this]() {
            long long last_count = -1;
            while (!shared_data_.stop && !solution_found_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
                long long current_count = shared_data_.max_count.load();
                if (current_count > last_count) {
                    last_count = current_count;
                    auto now = std::chrono::steady_clock::now();
                    auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time_).count();
                    std::cout << "[" << elapsed_ms << "ms] Progress: " << current_count << "/" << (board_size_ * board_size_)
                              << " pieces placed" << std::endl;
                }
            }
        });
    }

    // Wait for workers
    for (auto& t : threads) {
        t.join();
    }

    if (progress_thread.joinable()) {
        progress_thread.join();
    }

    // Aggregate statistics
    for (const auto& ts : thread_stats_) {
        shared_data_.stats.nodes_explored += ts.nodes_explored;
        shared_data_.stats.backtracks += ts.backtracks;
        shared_data_.stats.edge_incompatible += ts.edge_incompatible;
        if (ts.max_depth > shared_data_.stats.max_depth.load()) {
            shared_data_.stats.max_depth = ts.max_depth;
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
        return SolveResult::TIMEOUT;
    }

    return SolveResult::NO_SOLUTION;
}

void ParallelDLXSolver::worker_thread(size_t thread_id) {
    ThreadStats& stats = thread_stats_[thread_id];

    WorkUnit unit;
    while (work_queue_.pop(unit) && !shared_data_.stop && !solution_found_) {
        // Check again after pop (another thread might have found solution)
        if (shared_data_.stop || solution_found_) {
            break;
        }

        // Create local shared data for this solver
        // We use a local copy for stats, but the solver needs to check the main stop signal
        SharedData local_shared;
        local_shared.max_board = create_board(static_cast<int>(board_size_));
        local_shared.config = shared_data_.config;
        local_shared.config.verbose = false;  // No per-worker output
        
        // Set thread-specific random seed for diversification
        // If seed is 0 (default), use thread_id + time-based seed
        // If seed is set, use seed + thread_id for variation
        if (local_shared.config.random_seed == 0) {
            // Use thread_id + time-based component
            auto time_seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
            local_shared.config.random_seed = static_cast<uint32_t>(time_seed) + static_cast<uint32_t>(thread_id * 1000000);
        } else {
            // Use base seed + thread_id for variation
            local_shared.config.random_seed = shared_data_.config.random_seed + static_cast<uint32_t>(thread_id * 1000000);
        }
        
        // Initialize local stats (will be aggregated later)
        local_shared.stats.reset();
        // CRITICAL: Link stop signal to main shared_data so solver sees global stop
        // We'll sync this in the callback, but the solver checks shared_data_.stop directly
        // So we need to make sure the solver uses the main shared_data reference
        local_shared.stop.store(shared_data_.stop.load());

        // Set up callback to update main shared data
        local_shared.on_board_update = [this, &local_shared, thread_id](const Board& board) {
            // Check if global stop was set (solution found by another thread)
            if (shared_data_.stop.load()) {
                local_shared.stop.store(true);
            }

            // Count pieces
            long long piece_count = 0;
            for (size_t y = 0; y < board_size_; ++y) {
                for (size_t x = 0; x < board_size_; ++x) {
                    Index idx = {x, y};
                    const RotatedPiece* piece = get_piece(board, idx);
                    // get_piece always returns a pointer, check if piece is not EMPTY
                    if (piece->piece != EMPTY && piece->piece != 0) {
                        piece_count++;
                    }
                }
            }

            // Update main if better
            {
                std::scoped_lock lock(shared_data_.mutex);
                long long current_max = shared_data_.max_count.load();
                if (piece_count > current_max) {
                    shared_data_.max_count = piece_count;
                    shared_data_.max_board = board;

                    // Export partial solution if enabled
                    export_partial_solution(board,
                                          static_cast<size_t>(piece_count),
                                          shared_data_.config,
                                          shared_data_.puzzle_name);
                }
            }
        };

        // Create solver with local_shared, but we need to ensure it checks main stop signal
        // The solver's should_stop() checks shared_data_.stop, which is local_shared.stop
        // So we need to sync local_shared.stop with main shared_data_.stop
        // Actually, a better approach: create a wrapper that forwards stop checks to main
        // Use shared row metadata to avoid rebuilding the matrix
        DLXSolver solver(pieces_, board_size_, local_shared);
        // Replace the matrix with one using shared metadata (friend class can access private members)
        if (!shared_row_metadata_.empty()) {
            if (shared_data_.config.verbose && thread_id == 0) {
                std::cout << "[INFO] Worker threads using shared row metadata (" << shared_row_metadata_.size() << " rows) - skipping matrix rebuild" << std::endl;
            }
            auto worker_matrix_start = std::chrono::steady_clock::now();
            solver.matrix_ = DLXMatrix(board_size_, pieces_, shared_row_metadata_);
            solver.matrix_.build_matrix();  // Build structure using shared metadata
            auto worker_matrix_end = std::chrono::steady_clock::now();
            auto worker_matrix_ms = std::chrono::duration_cast<std::chrono::milliseconds>(worker_matrix_end - worker_matrix_start).count();
            if (shared_data_.config.verbose && thread_id == 0) {
                std::cout << "[INFO] Worker thread matrix structure built in " << worker_matrix_ms << " ms (using shared metadata)" << std::endl;
            }
        } else {
            if (shared_data_.config.verbose && thread_id == 0) {
                std::cout << "[WARN] No shared metadata available - worker threads will rebuild matrix from scratch" << std::endl;
            }
        }
        
        // Override the stop check by making local_shared.stop always reflect main stop
        // We'll do this by periodically syncing in the search, but that's complex
        // Instead, let's make the solver check the main shared_data_.stop directly
        // But the solver stores a reference to local_shared, so it will check local_shared.stop
        // Solution: sync local_shared.stop with main before each check, or pass main reference
        // For now, we'll sync it in the callback and hope the solver checks frequently enough

        // Set heuristic profile from work unit (portfolio search)
        if (shared_data_.config.portfolio_enabled) {
            solver.set_heuristic_profile(unit.profile);
        }

        // Log when first worker thread starts (only once)
        static std::atomic<bool> first_worker_logged{false};
        if (shared_data_.config.verbose && thread_id == 0 && !first_worker_logged.exchange(true)) {
            std::cout << "[INFO] Worker threads starting to solve work units..." << std::endl;
        }
        
        SolveResult result = solver.solve_from_partial(unit.partial_board);

        // Update stats
        stats.nodes_explored += local_shared.stats.nodes_explored;
        stats.backtracks += local_shared.stats.backtracks;
        stats.edge_incompatible += local_shared.stats.edge_incompatible;
        if (local_shared.stats.max_depth > stats.max_depth) {
            stats.max_depth = local_shared.stats.max_depth;
        }

        if (result == SolveResult::SOLVED) {
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
                    std::cout << "[INFO] Thread " << thread_id << " found solution!" << std::endl;
                }
            }
            break;
        }

        // Check if timeout or limit was reached
        if (result == SolveResult::TIMEOUT) {
            // Timeout reached - stop all threads
            shared_data_.stop = true;
            work_queue_.abort();

            if (shared_data_.config.verbose) {
                std::cout << "[INFO] Thread " << thread_id << " stopping (timeout reached)" << std::endl;
            }
            break;
        }

        // Check if global stop was triggered by another thread
        if (shared_data_.stop) {
            if (shared_data_.config.verbose) {
                std::cout << "[INFO] Thread " << thread_id << " stopping (solution found by other thread)" << std::endl;
            }
            break;
        }
    }

    if (shared_data_.config.verbose) {
        std::cout << "[INFO] Thread " << thread_id << " exiting - " << stats.nodes_explored << " nodes explored" << std::endl;
    }
}

bool ParallelDLXSolver::limits_reached() const {
    if (shared_data_.config.max_time_ms > 0) {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time_).count();
        if (static_cast<size_t>(elapsed) >= shared_data_.config.max_time_ms) {
            return true;
        }
    }

    if (shared_data_.config.max_nodes > 0) {
        if (shared_data_.stats.nodes_explored.load() >= shared_data_.config.max_nodes) {
            return true;
        }
    }

    return false;
}

} // namespace eternity2_v3
