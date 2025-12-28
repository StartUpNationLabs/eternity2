//
// Optimized Eternity II Solver v2 Implementation
//

#include "solver_v2.h"
#include "../heuristics/variable_ordering.h"

using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::WALL;
using eternity2_common::EMPTY;
using eternity2_common::UP_MASK;
using eternity2_common::RIGHT_MASK;
using eternity2_common::DOWN_MASK;
using eternity2_common::LEFT_MASK;
using eternity2_common::rotate_piece_right;
using eternity2_common::get_piece_part;
#include "../parallel/parallel_solver.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>

namespace eternity2_v2 {

const char* solve_result_to_string(SolveResult result) {
    switch (result) {
        case SolveResult::SOLVED: return "SOLVED";
        case SolveResult::NO_SOLUTION: return "NO_SOLUTION";
        case SolveResult::STOPPED: return "STOPPED";
        case SolveResult::TIMEOUT: return "TIMEOUT";
        case SolveResult::LIMIT_REACHED: return "LIMIT_REACHED";
        default: return "UNKNOWN";
    }
}

/**
 * @brief Export a partial solution to a CSV file
 *
 * @param board The board to export
 * @param pieces_placed Number of pieces placed so far
 * @param config Solver configuration with export settings
 * @param puzzle_name Name of the puzzle for BUCAS URL
 */
void export_partial_solution(const Board& board, size_t pieces_placed,
                            const SolverConfig& config, const std::string& puzzle_name) {
    if (!config.export_partial) {
        return;
    }

    // Generate filename with timestamp and piece count
    std::ostringstream filename;
    filename << config.export_dir << "/"
             << config.export_prefix << "_"
             << std::setfill('0') << std::setw(4) << pieces_placed
             << "_pieces.csv";

    // Export to file
    std::ofstream file(filename.str());
    if (!file.is_open()) {
        std::cerr << "Warning: Failed to open file for partial export: " << filename.str() << std::endl;
        return;
    }

    // Export board as CSV string with BUCAS URL
    std::string csv_content = export_board_to_csv_string(board, puzzle_name);
    file << csv_content;
    file.close();

    if (config.verbose) {
        std::cout << "Exported partial solution with " << pieces_placed
                  << " pieces to " << filename.str() << std::endl;
    }
}

SolverConfig config_from_profile(HeuristicProfile profile) {
    SolverConfig config;

    switch (profile) {
        case HeuristicProfile::MRV_LCV:
            // Default: MRV + Degree + LCV
            config.use_mrv = true;
            config.use_degree = true;
            config.use_lcv = true;
            config.use_reverse_lcv = false;
            break;

        case HeuristicProfile::MRV_RANDOM:
            // MRV + Degree + Random value ordering
            config.use_mrv = true;
            config.use_degree = true;
            config.use_lcv = false;
            config.use_reverse_lcv = false;
            break;

        case HeuristicProfile::MRV_ONLY_LCV:
            // MRV only (no degree tie-breaker) + LCV
            config.use_mrv = true;
            config.use_degree = false;
            config.use_lcv = true;
            config.use_reverse_lcv = false;
            break;

        case HeuristicProfile::STATIC_LCV:
            // Static ordering + LCV
            config.use_mrv = false;
            config.use_degree = false;
            config.use_lcv = true;
            config.use_reverse_lcv = false;
            break;

        case HeuristicProfile::MRV_REVERSE_LCV:
            // MRV + Degree + Reverse LCV (most constraining first)
            config.use_mrv = true;
            config.use_degree = true;
            config.use_lcv = true;
            config.use_reverse_lcv = true;
            break;

        case HeuristicProfile::STATIC_RANDOM:
            // Static ordering + Random
            config.use_mrv = false;
            config.use_degree = false;
            config.use_lcv = false;
            config.use_reverse_lcv = false;
            break;

        default:
            // Default to MRV + LCV
            config.use_mrv = true;
            config.use_degree = true;
            config.use_lcv = true;
            break;
    }

    return config;
}

SolverV2::SolverV2(const std::vector<Piece>& pieces, size_t board_size, SharedDataV2& shared_data)
    : pieces_(pieces)
    , board_size_(board_size)
    , board_(create_board(static_cast<int>(board_size)))
    , domain_manager_(board_size, pieces)
    , shared_data_(shared_data)
{
}

SolveResult SolverV2::solve() {
    // Initialize
    shared_data_.stats.reset();
    start_time_ = std::chrono::steady_clock::now();
    shared_data_.global_start_time = start_time_;  // Set global start time for non-parallel case

    // Initialize domains
    domain_manager_.initialize_domains();

    // Check for immediate failure (any empty domain)
    auto initial_check = select_next_variable();
    if (initial_check.is_failure) {
        shared_data_.stats.domain_wipeouts++;
        return SolveResult::NO_SOLUTION;
    }

    // Start search
    bool found = search(0);

    // Update elapsed time
    auto end_time = std::chrono::steady_clock::now();
    shared_data_.stats.elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time_).count();

    if (found) {
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

SolveResult SolverV2::solve_from_state(const Board& initial_board,
                                        const DomainManager& initial_domain,
                                        size_t initial_depth) {
    // Start from provided state (used by parallel solver for work units)
    start_time_ = std::chrono::steady_clock::now();

    // Copy the initial state
    board_ = initial_board;
    domain_manager_ = initial_domain;

    // Check for immediate failure
    auto initial_check = select_next_variable();
    if (initial_check.is_failure) {
        shared_data_.stats.domain_wipeouts++;
        return SolveResult::NO_SOLUTION;
    }

    // Start search from the given depth
    bool found = search(initial_depth);

    if (found) {
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

bool SolverV2::search(size_t depth) {
    // Update stats
    shared_data_.stats.nodes_explored++;
    if (depth > shared_data_.stats.max_depth) {
        shared_data_.stats.max_depth = depth;
    }

    // Check for stop signal or limits (unlikely during normal operation)
    if (__builtin_expect(shared_data_.stop || limits_reached(), 0)) {
        return false;
    }

    // Check if complete (unlikely until the very end)
    if (__builtin_expect(domain_manager_.is_complete(), 0)) {
        // Final verification: double-check that the solution is actually correct
        if (!verify_solution(board_)) {
            // Verification failed - this should not happen with proper constraint propagation
            // but we check anyway for safety
            if (shared_data_.config.verbose) {
                std::cerr << "WARNING: Solution verification failed!" << std::endl;
            }
            return false;
        }
        
        // Solution found and verified!
        shared_data_.max_board = board_;
        shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
        shared_data_.on_board_update(board_);
        return true;
    }

    // Select next variable (position to fill)
    VariableSelection var = select_next_variable();

    // Check for failure (empty domain detected) - relatively rare
    if (__builtin_expect(var.is_failure, 0)) {
        shared_data_.stats.domain_wipeouts++;
        return false;
    }

    // If no unassigned variables but not complete, something went wrong
    if (var.domain_size == 0) {
        return domain_manager_.is_complete();
    }

    // Get values to try
    const DomainEntry& domain = domain_manager_.get_domain(var.index);
    std::vector<RotatedPiece> values = order_values(var.index, domain.valid_pieces);

    // Update progress
    shared_data_.stats.pieces_placed = depth;
    update_best_board(depth);

    // Try each value
    for (const auto& piece : values) {
        // Check if piece is still available (might have been filtered)
        if (!domain_manager_.is_piece_available(piece.index)) {
            continue;
        }

        // Save state for backtracking
        domain_manager_.push_state();

        // Place piece on board
        place_piece(board_, piece, var.index);

        // Update domain manager (place piece and propagate constraints)
        bool consistent = domain_manager_.place_piece(var.index, piece);

        if (consistent) {
            // Notify callback
            shared_data_.on_board_update(board_);

            // Recurse
            if (search(depth + 1)) {
                return true;  // Solution found!
            }
        } else {
            // Domain wipeout detected during propagation
            shared_data_.stats.domain_wipeouts++;
        }

        // Backtrack
        shared_data_.stats.backtracks++;
        domain_manager_.pop_state();
        remove_piece(board_, var.index);
    }

    return false;
}

bool SolverV2::limits_reached() const {
    const auto& config = shared_data_.config;
    const auto& stats = shared_data_.stats;

    if (config.max_backtracks > 0 && stats.backtracks >= config.max_backtracks) {
        return true;
    }

    if (config.max_nodes > 0 && stats.nodes_explored >= config.max_nodes) {
        return true;
    }

    if (config.max_time_ms > 0) {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - shared_data_.global_start_time).count();
        if (static_cast<size_t>(elapsed) >= config.max_time_ms) {
            return true;
        }
    }

    return false;
}

void SolverV2::update_best_board(size_t depth) {
    if (static_cast<long long>(depth) > shared_data_.max_count) {
        std::scoped_lock lock(shared_data_.mutex);
        if (static_cast<long long>(depth) > shared_data_.max_count) {
            shared_data_.max_count = static_cast<long long>(depth);
            shared_data_.max_board = board_;
            shared_data_.stats.best_depth = depth;

            // Export partial solution if enabled
            export_partial_solution(board_, depth, shared_data_.config, shared_data_.puzzle_name);
        }
    }
}

VariableSelection SolverV2::select_next_variable() {
    const auto& config = shared_data_.config;

    // Check strategy first - border-first overrides MRV settings
    if (config.strategy == SolveStrategy::BORDER_FIRST) {
        return select_variable_border_first(domain_manager_);
    }

    // Standard MRV-based selection
    if (config.use_mrv) {
        if (config.use_degree) {
            return select_variable_mrv(domain_manager_);
        } else {
            return select_variable_mrv_simple(domain_manager_);
        }
    } else {
        return select_variable_static(domain_manager_);
    }
}

std::vector<RotatedPiece> SolverV2::order_values(Index index, const std::vector<RotatedPiece>& values) {
    const auto& config = shared_data_.config;

    if (config.use_lcv) {
        return order_values_lcv(domain_manager_, index, values);
    } else {
        return order_values_random(values);
    }
}

bool SolverV2::verify_solution(const Board& board) const {
    // Helper to get edge of a rotated piece in a specific direction
    auto get_edge = [](const RotatedPiece& rp, int direction) -> PiecePart {
        Piece rotated = rotate_piece_right(rp.piece, rp.rotation);
        switch (direction) {
            case 0: return get_piece_part(rotated, UP_MASK);    // UP
            case 1: return get_piece_part(rotated, RIGHT_MASK); // RIGHT
            case 2: return get_piece_part(rotated, DOWN_MASK);  // DOWN
            case 3: return get_piece_part(rotated, LEFT_MASK);   // LEFT
            default: return EMPTY;
        }
    };

    // 1. Check all positions are filled (non-empty pieces)
    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index idx = {x, y};
            const RotatedPiece* piece = get_piece(board, idx);
            if (piece->piece == EMPTY || piece->piece == 0) {
                return false;  // Empty position found
            }
        }
    }

    // 2. Check border edges are walls and interior edges match neighbors
    // 3. Check each piece is used exactly once
    std::vector<bool> piece_used(pieces_.size(), false);

    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index idx = {x, y};
            const RotatedPiece* piece = get_piece(board, idx);

            // Check piece index is valid
            if (piece->index < 0 || static_cast<size_t>(piece->index) >= pieces_.size()) {
                return false;
            }

            // Check piece is used exactly once
            if (piece_used[piece->index]) {
                return false;  // Piece used more than once
            }
            piece_used[piece->index] = true;

            // Check border edges are walls
            bool is_top = (y == 0);
            bool is_right = (x == board_size_ - 1);
            bool is_bottom = (y == board_size_ - 1);
            bool is_left = (x == 0);

            PiecePart up_edge = get_edge(*piece, 0);
            PiecePart right_edge = get_edge(*piece, 1);
            PiecePart down_edge = get_edge(*piece, 2);
            PiecePart left_edge = get_edge(*piece, 3);

            if (is_top && up_edge != WALL) {
                return false;  // Top border must be wall
            }
            if (is_right && right_edge != WALL) {
                return false;  // Right border must be wall
            }
            if (is_bottom && down_edge != WALL) {
                return false;  // Bottom border must be wall
            }
            if (is_left && left_edge != WALL) {
                return false;  // Left border must be wall
            }

            // Check interior edges match neighbors
            // Up neighbor
            if (!is_top) {
                Index up_idx = {x, y - 1};
                const RotatedPiece* up_piece = get_piece(board, up_idx);
                PiecePart up_neighbor_down_edge = get_edge(*up_piece, 2);
                if (up_edge != up_neighbor_down_edge) {
                    return false;  // Edges don't match
                }
            }

            // Right neighbor
            if (!is_right) {
                Index right_idx = {x + 1, y};
                const RotatedPiece* right_piece = get_piece(board, right_idx);
                PiecePart right_neighbor_left_edge = get_edge(*right_piece, 3);
                if (right_edge != right_neighbor_left_edge) {
                    return false;  // Edges don't match
                }
            }

            // Down neighbor
            if (!is_bottom) {
                Index down_idx = {x, y + 1};
                const RotatedPiece* down_piece = get_piece(board, down_idx);
                PiecePart down_neighbor_up_edge = get_edge(*down_piece, 0);
                if (down_edge != down_neighbor_up_edge) {
                    return false;  // Edges don't match
                }
            }

            // Left neighbor
            if (!is_left) {
                Index left_idx = {x - 1, y};
                const RotatedPiece* left_piece = get_piece(board, left_idx);
                PiecePart left_neighbor_right_edge = get_edge(*left_piece, 1);
                if (left_edge != left_neighbor_right_edge) {
                    return false;  // Edges don't match
                }
            }
        }
    }

    // 4. Verify exactly board_size * board_size pieces are used
    size_t pieces_used_count = 0;
    for (size_t i = 0; i < pieces_.size(); ++i) {
        if (piece_used[i]) {
            pieces_used_count++;
        }
    }
    
    size_t expected_pieces = board_size_ * board_size_;
    if (pieces_used_count != expected_pieces) {
        return false;  // Wrong number of pieces used
    }

    return true;  // All checks passed!
}

void solve_board_v2(Board& board, const std::vector<Piece>& pieces, SharedDataV2& shared_data) {
    SolveResult result;

    // Use parallel solver if enabled and more than 1 thread
    if (shared_data.config.parallel_enabled && shared_data.config.num_threads > 1) {
        ParallelSolverV2 parallel_solver(pieces, board.size, shared_data);
        result = parallel_solver.solve();

        if (result == SolveResult::SOLVED) {
            // Solution is already stored in shared_data.max_board by parallel solver
            board = shared_data.max_board;
        }
    } else {
        // Use single-threaded solver
        SolverV2 solver(pieces, board.size, shared_data);
        result = solver.solve();

        if (result == SolveResult::SOLVED) {
            board = solver.get_solution();
        }
    }

    shared_data.stop = true;

    if (shared_data.config.verbose) {
        const auto& stats = shared_data.stats;
        std::cout << "=== Solver v2 Results ===" << std::endl;
        std::cout << "Result: " << solve_result_to_string(result) << std::endl;
        if (shared_data.config.parallel_enabled) {
            std::cout << "Mode: Parallel (" << shared_data.config.num_threads << " threads)" << std::endl;
        } else {
            std::cout << "Mode: Single-threaded" << std::endl;
        }
        std::cout << "Nodes explored: " << stats.nodes_explored << std::endl;
        std::cout << "Backtracks: " << stats.backtracks << std::endl;
        std::cout << "Domain wipeouts: " << stats.domain_wipeouts << std::endl;
        std::cout << "Max depth: " << stats.max_depth << std::endl;
        std::cout << "Time: " << stats.elapsed_ms << " ms" << std::endl;
    }
}

} // namespace eternity2_v2
