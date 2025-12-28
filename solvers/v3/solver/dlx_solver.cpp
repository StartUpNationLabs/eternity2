//
// Dancing Links Solver Implementation
//

#include "dlx_solver.h"
#include "common/piece_utils.h"
#include "common/logger.h"
#include <algorithm>
#include <random>
#include <fstream>
#include <sstream>
#include <iomanip>

namespace eternity2_v3 {

DLXSolver::DLXSolver(const std::vector<Piece>& pieces, size_t board_size, SharedData& shared_data)
    : matrix_(board_size, pieces)
    , pieces_(pieces)
    , board_size_(board_size)
    , shared_data_(shared_data)
{
    // Initialize edge tracking
    for (auto& pos_edges : placed_edges_) {
        pos_edges.fill(0);
    }
    position_filled_.reset();

    // Initialize board
    board_ = create_board(static_cast<int>(board_size));

    // Pre-allocate buffers to avoid reallocations during search
    size_t num_positions = board_size * board_size;
    solution_.reserve(num_positions);
    propagation_trail_.reserve(num_positions * 4);  // Generous estimate
    propagation_queue_.reserve(num_positions);

    // Initialize RNG with seed from config (or default)
    uint32_t seed = shared_data_.config.random_seed;
    if (seed == 0) {
        // Use time-based seed if not specified
        seed = static_cast<uint32_t>(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    }
    init_rng(seed);
}

void DLXSolver::init_rng(uint32_t seed) {
    rng_state_ = seed;
    // Warm up RNG a bit to avoid correlation with seed
    for (int i = 0; i < 10; ++i) {
        next_random();
    }
}

SolveResult DLXSolver::solve() {
    // Build the matrix
    matrix_.build_matrix();

    // Reset statistics
    shared_data_.stats.reset();
    solution_.clear();
    position_filled_.reset();
    for (auto& pos_edges : placed_edges_) {
        pos_edges.fill(0);
    }

    // Start timing
    start_time_ = std::chrono::high_resolution_clock::now();

    // Run Algorithm X
    if (search(0)) {
        return SolveResult::SOLVED;
    }

    // Check why we stopped
    if (shared_data_.stop.load()) {
        return SolveResult::STOPPED;
    }

    if (should_stop()) {
        return SolveResult::TIMEOUT;
    }

    return SolveResult::NO_SOLUTION;
}

SolveResult DLXSolver::solve_from_partial(const Board& partial_board) {
    // Build matrix with partial board
    matrix_.build_from_partial(partial_board);

    // Reset statistics
    shared_data_.stats.reset();
    solution_.clear();

    // Initialize edge tracking from partial board
    position_filled_.reset();
    for (auto& pos_edges : placed_edges_) {
        pos_edges.fill(0);
    }

    // Pre-fill edges for placed pieces and count initial depth
    size_t initial_depth = 0;
    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index idx = {x, y};
            const RotatedPiece* piece = get_piece(partial_board, idx);

            if (piece != nullptr && piece->piece != EMPTY && piece->piece != 0) {
                size_t position = get_position(x, y);
                position_filled_.set(position);
                initial_depth++;  // Count pre-placed pieces

                // Compute edges
                Piece rotated = rotate_piece_right(piece->piece, piece->rotation);
                placed_edges_[position][DIR_UP] = get_piece_part(rotated, UP_MASK);
                placed_edges_[position][DIR_RIGHT] = get_piece_part(rotated, RIGHT_MASK);
                placed_edges_[position][DIR_DOWN] = get_piece_part(rotated, DOWN_MASK);
                placed_edges_[position][DIR_LEFT] = get_piece_part(rotated, LEFT_MASK);
            }
        }
    }

    // Copy partial board to our working board
    board_ = partial_board;

    // Initialize progress with pre-placed pieces
    if (initial_depth > 0) {
        update_best_progress(initial_depth);
        // Manually trigger callback to report initial progress (even if verbose is false in worker threads)
        // This ensures the progress thread sees the initial state
        // Always call the callback - it's set up in the worker thread to update shared_data
        shared_data_.on_board_update(board_);
    } else {
        // Even if no initial pieces, trigger callback to ensure it's working
        shared_data_.on_board_update(board_);
    }

    // Start timing
    start_time_ = std::chrono::high_resolution_clock::now();

    // Run Algorithm X (start from initial_depth since that many pieces are already placed)
    if (search(initial_depth)) {
        return SolveResult::SOLVED;
    }

    if (shared_data_.stop.load()) {
        return SolveResult::STOPPED;
    }

    if (should_stop()) {
        return SolveResult::TIMEOUT;
    }

    return SolveResult::NO_SOLUTION;
}

bool DLXSolver::search(size_t depth) {
    // Update statistics
    shared_data_.stats.nodes_explored++;

    if (depth > shared_data_.stats.max_depth.load()) {
        shared_data_.stats.max_depth = depth;
    }

    // Check stop conditions
    if (__builtin_expect(should_stop(), 0)) {
        return false;
    }

    // Check if matrix is empty (solution found)
    if (__builtin_expect(matrix_.is_empty(), 0)) {
        return handle_solution();
    }

    // Choose column based on heuristic profile
    DLXNode* col = choose_column_for_profile();

    // Empty column = dead end
    if (__builtin_expect(col == nullptr || col->size == 0, 0)) {
        shared_data_.stats.edge_incompatible++;  // Reusing for domain wipeout
        return false;
    }

    // Cover the column
    matrix_.cover(col);

    // Collect and order rows based on heuristic profile
    // Use local vector to avoid corruption during recursion
    std::vector<DLXNode*> ordered_rows;
    collect_and_order_rows(col, ordered_rows);

    // If no compatible rows, backtrack immediately
    if (ordered_rows.empty()) {
        shared_data_.stats.edge_incompatible++;
        matrix_.uncover(col);
        return false;
    }

    // Try each row in order
    for (DLXNode* row : ordered_rows) {
        const RowMetadata& meta = matrix_.get_row_metadata(row);

        // Add row to solution
        solution_.push_back(row);
        update_placed_edges(meta);

        // Update progress
        update_best_progress(depth + 1);

        // Cover all other columns in this row
        for (DLXNode* node = row->right; node != row; node = node->right) {
            matrix_.cover(node->column);
        }

        // Propagate constraints to neighbors (cover incompatible rows)
        size_t propagated = 0;
        bool prop_success = true;
        if (shared_data_.config.use_edge_propagation) {
            propagated = propagate_constraints(meta);
            prop_success = !propagation_failed_;
        }

        // Recurse only if propagation succeeded
        if (prop_success && search(depth + 1)) {
            return true;
        }

        // Backtrack: undo propagation first
        if (shared_data_.config.use_edge_propagation) {
            undo_propagation(propagated);
        }

        // Backtrack: uncover columns in reverse order
        for (DLXNode* node = row->left; node != row; node = node->left) {
            matrix_.uncover(node->column);
        }

        remove_placed_edges(meta);
        solution_.pop_back();
        shared_data_.stats.backtracks++;
    }

    // Uncover the column
    matrix_.uncover(col);

    return false;
}

bool DLXSolver::is_edge_compatible(const RowMetadata& row) const {
    size_t pos = static_cast<size_t>(row.position);
    size_t x = get_x(pos);
    size_t y = get_y(pos);

    // Check UP neighbor
    if (has_neighbor_up(pos)) {
        size_t up_pos = pos - board_size_;
        if (position_filled_.test(up_pos)) {
            // My UP edge must match neighbor's DOWN edge
            if (row.edge_up != placed_edges_[up_pos][DIR_DOWN]) {
                return false;
            }
        }
    }

    // Check RIGHT neighbor
    if (has_neighbor_right(pos)) {
        size_t right_pos = pos + 1;
        if (position_filled_.test(right_pos)) {
            // My RIGHT edge must match neighbor's LEFT edge
            if (row.edge_right != placed_edges_[right_pos][DIR_LEFT]) {
                return false;
            }
        }
    }

    // Check DOWN neighbor
    if (has_neighbor_down(pos)) {
        size_t down_pos = pos + board_size_;
        if (position_filled_.test(down_pos)) {
            // My DOWN edge must match neighbor's UP edge
            if (row.edge_down != placed_edges_[down_pos][DIR_UP]) {
                return false;
            }
        }
    }

    // Check LEFT neighbor
    if (has_neighbor_left(pos)) {
        size_t left_pos = pos - 1;
        if (position_filled_.test(left_pos)) {
            // My LEFT edge must match neighbor's RIGHT edge
            if (row.edge_left != placed_edges_[left_pos][DIR_RIGHT]) {
                return false;
            }
        }
    }

    return true;
}

void DLXSolver::update_placed_edges(const RowMetadata& row) {
    size_t pos = static_cast<size_t>(row.position);
    position_filled_.set(pos);

    placed_edges_[pos][DIR_UP] = row.edge_up;
    placed_edges_[pos][DIR_RIGHT] = row.edge_right;
    placed_edges_[pos][DIR_DOWN] = row.edge_down;
    placed_edges_[pos][DIR_LEFT] = row.edge_left;

    // Also place on board
    Index idx = {get_x(pos), get_y(pos)};
    RotatedPiece rp;
    rp.piece = pieces_[row.piece_index];
    rp.rotation = row.rotation;
    rp.index = row.piece_index;
    rp.edge_up = row.edge_up;
    rp.edge_right = row.edge_right;
    rp.edge_down = row.edge_down;
    rp.edge_left = row.edge_left;

    place_piece(board_, rp, idx);
}

void DLXSolver::remove_placed_edges(const RowMetadata& row) {
    size_t pos = static_cast<size_t>(row.position);
    position_filled_.reset(pos);

    placed_edges_[pos][DIR_UP] = 0;
    placed_edges_[pos][DIR_RIGHT] = 0;
    placed_edges_[pos][DIR_DOWN] = 0;
    placed_edges_[pos][DIR_LEFT] = 0;

    // Also remove from board
    Index idx = {get_x(pos), get_y(pos)};
    remove_piece(board_, idx);
}

bool DLXSolver::propagate_to_neighbor(size_t neighbor_pos, int required_dir, uint16_t required_edge,
                                       std::vector<size_t>& propagation_queue) {
    if (position_filled_.test(neighbor_pos)) {
        return true;  // Already filled, skip
    }

    DLXNode* col = matrix_.get_position_column(neighbor_pos);

    // Cover incompatible rows
    for (DLXNode* r = col->down; r != col; ) {
        DLXNode* next = r->down;  // Save next before potential removal
        const RowMetadata& neighbor_meta = matrix_.get_row_metadata(r);

        // Check if the required edge matches
        uint16_t neighbor_edge;
        switch (required_dir) {
            case DIR_UP:    neighbor_edge = neighbor_meta.edge_up; break;
            case DIR_RIGHT: neighbor_edge = neighbor_meta.edge_right; break;
            case DIR_DOWN:  neighbor_edge = neighbor_meta.edge_down; break;
            case DIR_LEFT:  neighbor_edge = neighbor_meta.edge_left; break;
            default: neighbor_edge = 0;
        }

        if (neighbor_edge != required_edge) {
            matrix_.cover_row(r);
            propagation_trail_.push_back(r);
        }
        r = next;
    }

    // Check for domain wipeout
    if (col->size == 0) {
        return false;  // Dead end
    }

    // If domain reduced to singleton, add to queue for cascade
    if (col->size == 1) {
        propagation_queue.push_back(neighbor_pos);
    }

    return true;
}

bool DLXSolver::propagate_constraints_cascade(const RowMetadata& row) {
    size_t pos = static_cast<size_t>(row.position);

    // Use pre-allocated queue and processed bitset (clear before use)
    propagation_queue_.clear();
    cascade_processed_.reset();

    // First pass: propagate to immediate neighbors
    // UP neighbor: their DOWN edge must match our UP edge
    if (has_neighbor_up(pos)) {
        if (!propagate_to_neighbor(pos - board_size_, DIR_DOWN, row.edge_up, propagation_queue_)) {
            return false;
        }
    }

    // RIGHT neighbor: their LEFT edge must match our RIGHT edge
    if (has_neighbor_right(pos)) {
        if (!propagate_to_neighbor(pos + 1, DIR_LEFT, row.edge_right, propagation_queue_)) {
            return false;
        }
    }

    // DOWN neighbor: their UP edge must match our DOWN edge
    if (has_neighbor_down(pos)) {
        if (!propagate_to_neighbor(pos + board_size_, DIR_UP, row.edge_down, propagation_queue_)) {
            return false;
        }
    }

    // LEFT neighbor: their RIGHT edge must match our LEFT edge
    if (has_neighbor_left(pos)) {
        if (!propagate_to_neighbor(pos - 1, DIR_RIGHT, row.edge_left, propagation_queue_)) {
            return false;
        }
    }

    // Cascade: process singleton positions (limited iterations to avoid pathological cases)
    size_t max_iterations = board_size_ * board_size_;  // At most one pass per position
    size_t iterations = 0;

    while (!propagation_queue_.empty() && iterations < max_iterations) {
        size_t singleton_pos = propagation_queue_.back();
        propagation_queue_.pop_back();
        iterations++;

        // Skip if already processed or filled
        if (cascade_processed_.test(singleton_pos) || position_filled_.test(singleton_pos)) {
            continue;
        }
        cascade_processed_.set(singleton_pos);

        DLXNode* col = matrix_.get_position_column(singleton_pos);

        // Check for wipeout (could have been wiped by another cascade)
        if (col->size == 0) {
            return false;
        }

        // Only cascade if still a singleton
        if (col->size == 1) {
            DLXNode* singleton_row = col->down;
            const RowMetadata& singleton_meta = matrix_.get_row_metadata(singleton_row);

            // Propagate singleton's constraints to its neighbors
            if (has_neighbor_up(singleton_pos)) {
                size_t neighbor = singleton_pos - board_size_;
                if (!cascade_processed_.test(neighbor)) {
                    if (!propagate_to_neighbor(neighbor, DIR_DOWN, singleton_meta.edge_up, propagation_queue_)) {
                        return false;
                    }
                }
            }
            if (has_neighbor_right(singleton_pos)) {
                size_t neighbor = singleton_pos + 1;
                if (!cascade_processed_.test(neighbor)) {
                    if (!propagate_to_neighbor(neighbor, DIR_LEFT, singleton_meta.edge_right, propagation_queue_)) {
                        return false;
                    }
                }
            }
            if (has_neighbor_down(singleton_pos)) {
                size_t neighbor = singleton_pos + board_size_;
                if (!cascade_processed_.test(neighbor)) {
                    if (!propagate_to_neighbor(neighbor, DIR_UP, singleton_meta.edge_down, propagation_queue_)) {
                        return false;
                    }
                }
            }
            if (has_neighbor_left(singleton_pos)) {
                size_t neighbor = singleton_pos - 1;
                if (!cascade_processed_.test(neighbor)) {
                    if (!propagate_to_neighbor(neighbor, DIR_RIGHT, singleton_meta.edge_left, propagation_queue_)) {
                        return false;
                    }
                }
            }
        }
    }

    return true;
}

size_t DLXSolver::propagate_constraints(const RowMetadata& row) {
    // Use cascade propagation and return the trail size for undo
    size_t trail_start = propagation_trail_.size();
    propagation_failed_ = !propagate_constraints_cascade(row);
    return propagation_trail_.size() - trail_start;
}

void DLXSolver::undo_propagation(size_t count) {
    // Uncover rows in reverse order
    for (size_t i = 0; i < count; ++i) {
        DLXNode* row = propagation_trail_.back();
        propagation_trail_.pop_back();
        matrix_.uncover_row(row);
    }
}

DLXNode* DLXSolver::choose_column_for_profile() {
    // Check if randomization is enabled
    bool use_random = shared_data_.config.randomization_strength > 0.0f;
    auto random_func = use_random ? [this]() { return random_float(); } : std::function<float()>();

    switch (heuristic_profile_) {
        case HeuristicProfile::BORDER_FIRST_LCV:
        case HeuristicProfile::BORDER_FIRST_RANDOM:
        case HeuristicProfile::CORNER_HEAVY:
        case HeuristicProfile::RARE_COLOR_FIRST:
        case HeuristicProfile::REVERSE_LCV:
            // All these use border-first column selection
            return matrix_.choose_column_smart(use_random, random_func);

        case HeuristicProfile::S_HEURISTIC_LCV:
        default:
            // Pure S-heuristic (original behavior)
            return matrix_.choose_column(use_random, random_func);
    }
}

void DLXSolver::collect_and_order_rows(DLXNode* column, std::vector<DLXNode*>& ordered_rows) {
    ordered_rows.clear();

    // Collect all edge-compatible rows
    for (DLXNode* row = column->down; row != column; row = row->down) {
        if (shared_data_.config.use_edge_propagation) {
            if (is_edge_compatible(matrix_.get_row_metadata(row))) {
                ordered_rows.push_back(row);
            }
        } else {
            ordered_rows.push_back(row);
        }
    }

    // Check if partial randomization is enabled
    float rand_strength = shared_data_.config.randomization_strength;
    bool use_partial_random = (rand_strength > 0.0f && rand_strength < 1.0f);

    // Order based on heuristic profile
    switch (heuristic_profile_) {
        case HeuristicProfile::BORDER_FIRST_LCV:
        case HeuristicProfile::S_HEURISTIC_LCV:
        case HeuristicProfile::CORNER_HEAVY:
            // LCV: higher score = more common colors = less constraining = try first
            std::sort(ordered_rows.begin(), ordered_rows.end(),
                [this](DLXNode* a, DLXNode* b) {
                    return matrix_.get_row_metadata(a).lcv_score > matrix_.get_row_metadata(b).lcv_score;
                });
            
            // Partial randomization: shuffle within LCV buckets
            if (use_partial_random) {
                // Group rows by LCV score (within tolerance)
                // Shuffle rows with similar LCV scores
                if (ordered_rows.size() > 1) {
                    int16_t bucket_size = static_cast<int16_t>(rand_strength * 10.0f); // Bucket size based on strength
                    if (bucket_size > 0) {
                        for (size_t i = 0; i < ordered_rows.size(); ) {
                            int16_t current_score = matrix_.get_row_metadata(ordered_rows[i]).lcv_score;
                            size_t bucket_start = i;
                            
                            // Find end of bucket (rows with similar LCV scores)
                            while (i < ordered_rows.size() && 
                                   std::abs(matrix_.get_row_metadata(ordered_rows[i]).lcv_score - current_score) <= bucket_size) {
                                i++;
                            }
                            
                            // Shuffle within bucket if it has multiple elements
                            if (i - bucket_start > 1) {
                                for (size_t j = bucket_start; j < i - 1; ++j) {
                                    size_t k = j + (next_random() % (i - j));
                                    std::swap(ordered_rows[j], ordered_rows[k]);
                                }
                            }
                        }
                    }
                }
            }
            break;

        case HeuristicProfile::RARE_COLOR_FIRST:
        case HeuristicProfile::REVERSE_LCV:
            // Reverse LCV: try most constraining first (for diversity)
            std::sort(ordered_rows.begin(), ordered_rows.end(),
                [this](DLXNode* a, DLXNode* b) {
                    return matrix_.get_row_metadata(a).lcv_score < matrix_.get_row_metadata(b).lcv_score;
                });
            
            // Partial randomization: shuffle within reverse LCV buckets
            if (use_partial_random) {
                if (ordered_rows.size() > 1) {
                    int16_t bucket_size = static_cast<int16_t>(rand_strength * 10.0f);
                    if (bucket_size > 0) {
                        for (size_t i = 0; i < ordered_rows.size(); ) {
                            int16_t current_score = matrix_.get_row_metadata(ordered_rows[i]).lcv_score;
                            size_t bucket_start = i;
                            
                            while (i < ordered_rows.size() && 
                                   std::abs(matrix_.get_row_metadata(ordered_rows[i]).lcv_score - current_score) <= bucket_size) {
                                i++;
                            }
                            
                            if (i - bucket_start > 1) {
                                for (size_t j = bucket_start; j < i - 1; ++j) {
                                    size_t k = j + (next_random() % (i - j));
                                    std::swap(ordered_rows[j], ordered_rows[k]);
                                }
                            }
                        }
                    }
                }
            }
            break;

        case HeuristicProfile::BORDER_FIRST_RANDOM:
            // Random shuffle (Fisher-Yates using our LCG)
            for (size_t i = ordered_rows.size(); i > 1; --i) {
                size_t j = next_random() % i;
                std::swap(ordered_rows[i - 1], ordered_rows[j]);
            }
            break;

        default:
            // No ordering, use matrix order
            break;
    }
}

bool DLXSolver::handle_solution() {
    shared_data_.stats.solutions_found++;

    // Build board from solution
    build_board_from_solution();

    // Verify solution
    if (!verify_solution()) {
        return false;
    }

    // Update shared data
    {
        std::lock_guard<std::mutex> lock(shared_data_.mutex);
        shared_data_.max_board = board_;
        shared_data_.max_count = static_cast<long long>(board_size_ * board_size_);
    }

    shared_data_.on_board_update(board_);

    return true;
}

void DLXSolver::build_board_from_solution() {
    // Board is already built incrementally during search
    // This function can be used if we need to rebuild from solution_ vector
}

bool DLXSolver::verify_solution() const {
    size_t num_positions = board_size_ * board_size_;

    // Check all positions are filled
    for (size_t pos = 0; pos < num_positions; ++pos) {
        if (!position_filled_.test(pos)) {
            return false;
        }
    }

    // Check all internal edges match
    for (size_t pos = 0; pos < num_positions; ++pos) {
        size_t x = get_x(pos);
        size_t y = get_y(pos);

        // Check RIGHT edge
        if (x < board_size_ - 1) {
            size_t right_pos = pos + 1;
            if (placed_edges_[pos][DIR_RIGHT] != placed_edges_[right_pos][DIR_LEFT]) {
                return false;
            }
        }

        // Check DOWN edge
        if (y < board_size_ - 1) {
            size_t down_pos = pos + board_size_;
            if (placed_edges_[pos][DIR_DOWN] != placed_edges_[down_pos][DIR_UP]) {
                return false;
            }
        }
    }

    return true;
}

bool DLXSolver::should_stop() const {
    if (shared_data_.stop.load()) {
        return true;
    }

    // Check timeout
    if (shared_data_.config.max_time_ms > 0) {
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time_).count();
        if (static_cast<size_t>(elapsed) >= shared_data_.config.max_time_ms) {
            return true;
        }
    }

    // Check node limit
    if (shared_data_.config.max_nodes > 0) {
        if (shared_data_.stats.nodes_explored.load() >= shared_data_.config.max_nodes) {
            return true;
        }
    }

    return false;
}

void DLXSolver::update_best_progress(size_t depth) {
    size_t current_best = shared_data_.stats.best_depth.load();
    if (depth > current_best) {
        shared_data_.stats.best_depth = depth;

        // Update max_count for progress reporting
        long long expected = static_cast<long long>(current_best);
        shared_data_.max_count.compare_exchange_weak(expected, static_cast<long long>(depth));

        // Always trigger callback - it handles partial solution export and progress reporting
        // The callback is set up in worker threads to update shared_data even if verbose is false
        shared_data_.on_board_update(board_);
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

} // namespace eternity2_v3
