//
// Parallel Eternity II Solver v2 Implementation
// Uses Embarrassingly Parallel Search (EPS) with std::thread
//

#include "parallel_solver.h"
#include <iostream>
#include <algorithm>

namespace eternity2_v2 {

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

    // Initialize a temporary domain manager to get initial choices
    DomainManager temp_domain(board_size_, pieces_);
    temp_domain.initialize_domains();

    // Get first position using MRV (typically a corner with few valid pieces)
    VariableSelection first_var = select_next_variable(temp_domain);
    if (first_var.is_failure) {
        shared_data_.stats.domain_wipeouts++;
        return SolveResult::NO_SOLUTION;
    }

    // Get all valid pieces for first position
    const DomainEntry& first_domain = temp_domain.get_domain(first_var.index);
    std::vector<RotatedPiece> initial_choices = first_domain.valid_pieces;

    if (initial_choices.empty()) {
        return SolveResult::NO_SOLUTION;
    }

    // Limit threads to number of initial choices
    size_t effective_threads = std::min(num_threads_, initial_choices.size());

    if (shared_data_.config.verbose) {
        std::cout << "Parallel solver starting with " << effective_threads << " threads" << std::endl;
        std::cout << "First position: (" << first_var.index.first << ", " << first_var.index.second << ")" << std::endl;
        std::cout << "Initial choices: " << initial_choices.size() << std::endl;
    }

    // Initialize per-thread stats
    thread_stats_.resize(effective_threads);
    for (auto& ts : thread_stats_) {
        ts = ThreadStats{};
    }

    // Calculate work distribution
    size_t choices_per_thread = initial_choices.size() / effective_threads;
    size_t remainder = initial_choices.size() % effective_threads;

    // Launch worker threads
    std::vector<std::thread> threads;
    threads.reserve(effective_threads);

    size_t start = 0;
    for (size_t t = 0; t < effective_threads; ++t) {
        size_t count = choices_per_thread + (t < remainder ? 1 : 0);
        size_t end = start + count;

        threads.emplace_back(&ParallelSolverV2::worker_thread, this,
                            t, first_var.index, std::cref(initial_choices), start, end);
        start = end;
    }

    // Wait for all threads to complete
    for (auto& t : threads) {
        t.join();
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

    // Update elapsed time
    auto end_time = std::chrono::steady_clock::now();
    shared_data_.stats.elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time).count();

    if (solution_found_) {
        shared_data_.stats.solutions_found++;
        return SolveResult::SOLVED;
    }

    if (shared_data_.stop) {
        return SolveResult::STOPPED;
    }

    if (limits_reached()) {
        if (shared_data_.config.max_time_ms > 0) {
            return SolveResult::TIMEOUT;
        }
        return SolveResult::LIMIT_REACHED;
    }

    return SolveResult::NO_SOLUTION;
}

void ParallelSolverV2::worker_thread(size_t thread_id,
                                     Index first_position,
                                     const std::vector<RotatedPiece>& initial_choices,
                                     size_t start_idx,
                                     size_t end_idx) {
    ThreadStats& stats = thread_stats_[thread_id];

    for (size_t i = start_idx; i < end_idx && !shared_data_.stop && !solution_found_; ++i) {
        const RotatedPiece& first_piece = initial_choices[i];

        // Create thread-local board and domain manager
        Board board = create_board(static_cast<int>(board_size_));
        DomainManager domain_manager(board_size_, pieces_);
        domain_manager.initialize_domains();

        // Place the first piece
        place_piece(board, first_piece, first_position);

        if (!domain_manager.place_piece(first_position, first_piece)) {
            stats.domain_wipeouts++;
            continue;  // Invalid first choice, try next
        }

        stats.nodes_explored++;

        // Search from depth 1
        if (search_recursive(board, domain_manager, 1, stats)) {
            // Solution found!
            solution_found_ = true;
            shared_data_.stop = true;

            // Update shared solution (thread-safe with mutex)
            {
                std::scoped_lock lock(shared_data_.mutex);
                shared_data_.max_board = board;
                shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
            }

            if (shared_data_.config.verbose) {
                std::cout << "Thread " << thread_id << " found solution!" << std::endl;
            }
            break;
        }
    }

    if (shared_data_.config.verbose && !solution_found_) {
        std::cout << "Thread " << thread_id << " completed range ["
                  << start_idx << ", " << end_idx << ") - "
                  << stats.nodes_explored << " nodes explored" << std::endl;
    }
}

bool ParallelSolverV2::search_recursive(Board& board,
                                        DomainManager& domain_manager,
                                        size_t depth,
                                        ThreadStats& stats) {
    // Update local stats
    stats.nodes_explored++;
    if (depth > stats.max_depth) {
        stats.max_depth = depth;
    }

    // Check for stop signal or limits
    if (shared_data_.stop || solution_found_ || limits_reached()) {
        return false;
    }

    // Check if complete
    if (domain_manager.is_complete()) {
        return true;  // Solution found!
    }

    // Select next variable (position to fill)
    VariableSelection var = select_next_variable(domain_manager);

    // Check for failure (empty domain detected)
    if (var.is_failure) {
        stats.domain_wipeouts++;
        return false;
    }

    // If no unassigned variables but not complete, something went wrong
    if (var.domain_size == 0) {
        return domain_manager.is_complete();
    }

    // Get values to try
    const DomainEntry& domain = domain_manager.get_domain(var.index);
    std::vector<RotatedPiece> values = order_values(domain_manager, var.index, domain.valid_pieces);

    // Update shared best board progress (thread-safe)
    if (static_cast<long long>(depth) > shared_data_.max_count) {
        std::scoped_lock lock(shared_data_.mutex);
        if (static_cast<long long>(depth) > shared_data_.max_count) {
            shared_data_.max_count = static_cast<long long>(depth);
            shared_data_.max_board = board;
            shared_data_.stats.best_depth = depth;
        }
    }

    // Try each value
    for (const auto& piece : values) {
        // Check if piece is still available
        if (!domain_manager.is_piece_available(piece.index)) {
            continue;
        }

        // Check for stop signal (check periodically to avoid overhead)
        if (shared_data_.stop || solution_found_) {
            return false;
        }

        // Save state for backtracking
        domain_manager.push_state();

        // Place piece on board
        place_piece(board, piece, var.index);

        // Update domain manager (place piece and propagate constraints)
        bool consistent = domain_manager.place_piece(var.index, piece);

        if (consistent) {
            // Recurse
            if (search_recursive(board, domain_manager, depth + 1, stats)) {
                return true;  // Solution found!
            }
        } else {
            // Domain wipeout detected during propagation
            stats.domain_wipeouts++;
        }

        // Backtrack
        stats.backtracks++;
        domain_manager.pop_state();
        remove_piece(board, var.index);
    }

    return false;
}

VariableSelection ParallelSolverV2::select_next_variable(const DomainManager& domain_manager) {
    const auto& config = shared_data_.config;

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
                                                         const std::vector<RotatedPiece>& values) {
    const auto& config = shared_data_.config;

    if (config.use_lcv) {
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

    // Note: Time limit checking is approximate in parallel mode
    // The main solve() function tracks overall time more accurately

    return false;
}

} // namespace eternity2_v2
