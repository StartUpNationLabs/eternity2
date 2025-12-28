//
// Dancing Links Matrix
// Sparse matrix implementation for exact cover solving
//

#ifndef ETERNITY2_V3_DLX_MATRIX_H
#define ETERNITY2_V3_DLX_MATRIX_H

#include "dlx_node.h"
#include "common/types.h"
#include "v1/board/board.h"
#include <vector>
#include <array>
#include <memory>
#include <functional>

namespace eternity2_v3 {

using namespace eternity2_common;

/**
 * @brief Dancing Links sparse matrix for exact cover
 *
 * The matrix represents the Eternity II puzzle as an exact cover problem:
 * - Columns 0 to (num_pieces-1): Piece P is used
 * - Columns num_pieces to (num_pieces + num_positions - 1): Position (x,y) is filled
 *
 * Each row represents a valid placement: (piece, position, rotation)
 */
class DLXMatrix {
public:
    /**
     * @brief Construct a DLX matrix for the given puzzle
     *
     * @param board_size Size of the board (NxN)
     * @param pieces Vector of piece data
     */
    DLXMatrix(size_t board_size, const std::vector<Piece>& pieces);

    /**
     * @brief Construct a DLX matrix with shared row metadata
     *
     * This constructor allows sharing read-only row_metadata_ between threads
     * to avoid rebuilding the matrix structure multiple times.
     *
     * @param board_size Size of the board (NxN)
     * @param pieces Vector of piece data
     * @param shared_row_metadata Reference to row metadata from another matrix
     */
    DLXMatrix(size_t board_size, const std::vector<Piece>& pieces,
              const std::vector<RowMetadata>& shared_row_metadata);

    /**
     * @brief Build the matrix by generating all valid placement rows
     *
     * Pre-filters placements by:
     * - Border pieces must have WALL edges on borders
     * - Interior pieces must not have WALL edges facing interior
     */
    void build_matrix();

    /**
     * @brief Build matrix from a partial board (hint support)
     *
     * Covers columns for pieces/positions already filled in the partial board.
     *
     * @param partial_board Board with some pieces pre-placed
     */
    void build_from_partial(const Board& partial_board);

    /**
     * @brief Cover a column (remove it and all rows containing it)
     *
     * O(1) pointer manipulation for column header removal.
     * For each row in the column, removes all other nodes in that row
     * from their respective columns.
     *
     * @param column Column header to cover
     */
    void cover(DLXNode* column);

    /**
     * @brief Uncover a column (restore it and all rows containing it)
     *
     * Reverses cover operation in O(1) per node.
     * Must be called in reverse order of cover calls.
     *
     * @param column Column header to uncover
     */
    void uncover(DLXNode* column);

    /**
     * @brief Choose column with minimum size (S-heuristic)
     *
     * Implements Knuth's S-heuristic: choose the column with the
     * fewest remaining rows. This minimizes branching factor.
     *
     * @param random_tiebreak If true, randomly select among columns with same size
     * @param random_func Function to generate random numbers (for tie-breaking)
     * @return Column header with minimum size, or nullptr if empty
     */
    DLXNode* choose_column(bool random_tiebreak = false, std::function<float()> random_func = nullptr);

    /**
     * @brief Choose column with border-first + S-heuristic
     *
     * Implements position-aware column selection:
     * 1. Prioritize position columns over piece columns
     * 2. Within positions: corners > edges > interior
     * 3. Use S-heuristic (min size) as tiebreaker
     * 4. Optional random tie-breaking for diversification
     *
     * @param random_tiebreak If true, randomly select among columns with same score
     * @param random_func Function to generate random numbers (for tie-breaking)
     * @return Column header selected by border-first heuristic
     */
    DLXNode* choose_column_smart(bool random_tiebreak = false, std::function<float()> random_func = nullptr);

    /**
     * @brief Get position type for a given position
     */
    PositionType get_position_type(size_t position) const {
        return position_types_[position];
    }

    /**
     * @brief Get color frequency for LCV scoring
     */
    uint16_t get_color_frequency(uint16_t color) const {
        return color_frequency_[color];
    }

    /**
     * @brief Get the root (master header) node
     */
    DLXNode* root() { return &root_; }

    /**
     * @brief Check if the matrix is empty (all columns covered)
     */
    bool is_empty() const { return root_.right == &root_; }

    /**
     * @brief Get row metadata for edge compatibility checking
     */
    const RowMetadata& get_row_metadata(size_t row_id) const {
        if (uses_shared_metadata_ && shared_row_metadata_ != nullptr) {
            return (*shared_row_metadata_)[row_id];
        }
        return row_metadata_[row_id];
    }

    /**
     * @brief Get row metadata from a node
     */
    const RowMetadata& get_row_metadata(const DLXNode* node) const;

    /**
     * @brief Get the number of columns
     */
    size_t num_columns() const { return num_columns_; }

    /**
     * @brief Get the number of rows
     */
    size_t num_rows() const {
        if (uses_shared_metadata_ && shared_row_metadata_ != nullptr) {
            return shared_row_metadata_->size();
        }
        return row_metadata_.size();
    }

    /**
     * @brief Get board size
     */
    size_t board_size() const { return board_size_; }

    /**
     * @brief Get number of pieces
     */
    size_t num_pieces() const { return pieces_.size(); }

    /**
     * @brief Get column header by ID
     */
    DLXNode* get_column(size_t column_id) {
        return &column_headers_[column_id];
    }

    /**
     * @brief Get position column header
     */
    DLXNode* get_position_column(size_t position) {
        return &column_headers_[pieces_.size() + position];
    }

    /**
     * @brief Cover a single row (remove from all its columns)
     *
     * Used for constraint propagation - removes incompatible rows
     * without covering the entire column.
     */
    void cover_row(DLXNode* row_node);

    /**
     * @brief Uncover a single row (restore to all its columns)
     *
     * Reverses cover_row operation.
     */
    void uncover_row(DLXNode* row_node);

    /**
     * @brief Get all row metadata for a position
     *
     * Returns iterators to traverse all rows in a position column.
     */
    std::pair<DLXNode*, DLXNode*> get_position_rows(size_t position) {
        DLXNode* col = get_position_column(position);
        return {col->down, col};
    }

    /**
     * @brief Get reference to row metadata (for sharing between threads)
     *
     * @return Const reference to row_metadata_ vector
     */
    const std::vector<RowMetadata>& get_row_metadata_ref() const {
        return row_metadata_;
    }

private:
    // Master header (root)
    DLXNode root_;

    // Column headers (piece columns + position columns)
    std::vector<DLXNode> column_headers_;

    // All nodes in the matrix (contiguous for cache efficiency)
    std::vector<DLXNode> nodes_;

    // Row metadata for edge checking
    // Can be shared between threads (read-only after building)
    std::vector<RowMetadata> row_metadata_;
    const std::vector<RowMetadata>* shared_row_metadata_ = nullptr;  // Pointer to shared metadata (if used)
    bool uses_shared_metadata_ = false;  // Flag to track if metadata is shared

    // Row start pointers (first node of each row)
    std::vector<DLXNode*> row_starts_;

    // Puzzle data
    size_t board_size_;
    size_t num_positions_;
    size_t num_columns_;
    std::vector<Piece> pieces_;

    // Position type cache for border-first heuristic
    static constexpr size_t MAX_POSITIONS = 256;  // 16x16 max
    std::array<PositionType, MAX_POSITIONS> position_types_;

    // Color frequency for LCV scoring (max 32 colors typical)
    static constexpr size_t MAX_COLORS = 32;
    std::array<uint16_t, MAX_COLORS> color_frequency_;

    // Helper methods
    void create_column_headers();
    bool is_valid_placement(size_t piece_idx, size_t position, int rotation) const;
    void add_row(size_t piece_idx, size_t position, int rotation);
    void link_node_to_column(DLXNode* node, DLXNode* column);
    void link_nodes_horizontally(const std::vector<DLXNode*>& row_nodes);

    // Precomputation helpers
    void precompute_position_types();
    void compute_color_frequencies();

    // Get coordinate from 1D position
    size_t get_x(size_t position) const { return position % board_size_; }
    size_t get_y(size_t position) const { return position / board_size_; }
    size_t get_position(size_t x, size_t y) const { return y * board_size_ + x; }
};

} // namespace eternity2_v3

#endif // ETERNITY2_V3_DLX_MATRIX_H
