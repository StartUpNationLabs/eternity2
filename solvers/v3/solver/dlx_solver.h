//
// Dancing Links Solver
// Algorithm X implementation with edge propagation
//

#ifndef ETERNITY2_V3_DLX_SOLVER_H
#define ETERNITY2_V3_DLX_SOLVER_H

#include "dlx/dlx_matrix.h"
#include "config/solver_config.h"
#include "common/types.h"
#include "v1/board/board.h"
#include <vector>
#include <array>
#include <bitset>
#include <chrono>

namespace eternity2_v3 {

using namespace eternity2_common;

// Maximum board size supported
constexpr size_t MAX_BOARD_SIZE = 16;
constexpr size_t MAX_POSITIONS = MAX_BOARD_SIZE * MAX_BOARD_SIZE;

/**
 * @brief Dancing Links solver for Eternity II
 *
 * Implements Algorithm X with the hybrid approach:
 * - DLX for exact cover (piece placement + position coverage)
 * - Edge compatibility checking during search
 */
class ParallelDLXSolver;  // Forward declaration

class DLXSolver {
    friend class ParallelDLXSolver;  // Allow parallel solver to access internals

public:
    /**
     * @brief Construct solver with pieces and shared data
     */
    DLXSolver(const std::vector<Piece>& pieces, size_t board_size, SharedData& shared_data);

    /**
     * @brief Solve from empty board
     */
    SolveResult solve();

    /**
     * @brief Solve from partial board (hint support)
     */
    SolveResult solve_from_partial(const Board& partial_board);

    /**
     * @brief Get the solution board
     */
    const Board& get_solution() const { return board_; }

    /**
     * @brief Set the heuristic profile for this solver instance
     */
    void set_heuristic_profile(HeuristicProfile profile) {
        heuristic_profile_ = profile;
    }

    /**
     * @brief Get current heuristic profile
     */
    HeuristicProfile get_heuristic_profile() const {
        return heuristic_profile_;
    }

private:
    // Core search
    bool search(size_t depth);

    // Column selection based on heuristic profile
    DLXNode* choose_column_for_profile();

    // Row ordering for LCV/random heuristics
    void collect_and_order_rows(DLXNode* column, std::vector<DLXNode*>& ordered_rows);

    // Edge compatibility (hybrid approach)
    bool is_edge_compatible(const RowMetadata& row) const;
    void update_placed_edges(const RowMetadata& row);
    void remove_placed_edges(const RowMetadata& row);

    // Constraint propagation - cover incompatible rows in neighbors
    size_t propagate_constraints(const RowMetadata& row);
    void undo_propagation(size_t count);

    // Cascade propagation helpers
    bool propagate_constraints_cascade(const RowMetadata& row);
    bool propagate_to_neighbor(size_t neighbor_pos, int required_dir, uint16_t required_edge,
                               std::vector<size_t>& propagation_queue);

    // Solution handling
    bool handle_solution();
    void build_board_from_solution();
    bool verify_solution() const;

    // Limits checking
    bool should_stop() const;
    void update_best_progress(size_t depth);

    // Coordinate helpers
    size_t get_x(size_t position) const { return position % board_size_; }
    size_t get_y(size_t position) const { return position / board_size_; }
    size_t get_position(size_t x, size_t y) const { return y * board_size_ + x; }
    bool has_neighbor_up(size_t position) const { return get_y(position) > 0; }
    bool has_neighbor_right(size_t position) const { return get_x(position) < board_size_ - 1; }
    bool has_neighbor_down(size_t position) const { return get_y(position) < board_size_ - 1; }
    bool has_neighbor_left(size_t position) const { return get_x(position) > 0; }

    // Data
    DLXMatrix matrix_;
    std::vector<Piece> pieces_;
    size_t board_size_;
    SharedData& shared_data_;

    // Current solution (nodes selected)
    std::vector<DLXNode*> solution_;

    // Board representation
    Board board_;

    // Edge tracking for compatibility checking
    // For each position, store the 4 edges (UP, RIGHT, DOWN, LEFT)
    // Value 0 means no piece placed (or edge is at border)
    std::array<std::array<uint16_t, 4>, MAX_POSITIONS> placed_edges_;
    std::bitset<MAX_POSITIONS> position_filled_;

    // Trail for constraint propagation - tracks covered rows for backtracking
    // Pre-allocated to avoid reallocations during search
    std::vector<DLXNode*> propagation_trail_;

    // Pre-allocated propagation queue for cascade propagation
    std::vector<size_t> propagation_queue_;

    // Bitset for tracking processed positions during cascade (avoid duplicates)
    std::bitset<MAX_POSITIONS> cascade_processed_;

    // Flag set when cascade propagation detects domain wipeout
    bool propagation_failed_ = false;

    // Timing
    std::chrono::high_resolution_clock::time_point start_time_;

    // Heuristic profile for this solver instance
    HeuristicProfile heuristic_profile_ = HeuristicProfile::BORDER_FIRST_LCV;

    // Simple LCG random number generator for deterministic randomness per thread
    uint32_t rng_state_ = 12345;
    uint32_t next_random() {
        rng_state_ = rng_state_ * 1103515245 + 12345;
        return (rng_state_ >> 16) & 0x7fff;
    }

    // Initialize RNG with seed (called from constructor or setter)
    void init_rng(uint32_t seed);
    
    // Get random float in [0, 1)
    float random_float() {
        return static_cast<float>(next_random()) / 32768.0f;
    }

    // Direction constants
    static constexpr int DIR_UP = 0;
    static constexpr int DIR_RIGHT = 1;
    static constexpr int DIR_DOWN = 2;
    static constexpr int DIR_LEFT = 3;

    // Opposite direction lookup
    static constexpr int opposite_dir(int dir) {
        return (dir + 2) % 4;
    }
};

/**
 * @brief Export a partial solution to a CSV file
 *
 * @param board The board to export
 * @param pieces_placed Number of pieces placed so far
 * @param config Solver configuration with export settings
 * @param puzzle_name Name of the puzzle for BUCAS URL
 */
void export_partial_solution(const Board& board, size_t pieces_placed,
                            const SolverConfig& config, const std::string& puzzle_name);

} // namespace eternity2_v3

#endif // ETERNITY2_V3_DLX_SOLVER_H
