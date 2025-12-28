//
// Dancing Links Node Structure
// Core building block for the DLX sparse matrix
//

#ifndef ETERNITY2_V3_DLX_NODE_H
#define ETERNITY2_V3_DLX_NODE_H

#include <cstdint>
#include <cstddef>

namespace eternity2_v3 {

/**
 * @brief Dancing Links node for exact cover matrix
 *
 * Each node is part of two circular doubly-linked lists:
 * - Horizontal (left/right) linking nodes in the same row
 * - Vertical (up/down) linking nodes in the same column
 *
 * Column headers are special nodes that track column size.
 */
struct DLXNode {
    DLXNode* left = nullptr;
    DLXNode* right = nullptr;
    DLXNode* up = nullptr;
    DLXNode* down = nullptr;
    DLXNode* column = nullptr;  // Points to column header (nullptr for headers)

    // Row identification data (for regular nodes)
    int16_t piece_index = -1;    // Original piece index (0-255)
    int16_t position = -1;       // 1D board position (y * size + x)
    int8_t rotation = 0;         // Rotation (0-3)
    size_t row_id = 0;           // Index into row_metadata_ for O(1) lookup

    // Column header data (for column headers only)
    int32_t size = 0;            // Number of nodes in this column
    int32_t column_id = -1;      // Column identifier

    // Check if this is a column header
    [[gnu::always_inline]] bool is_header() const {
        return column == nullptr || column == this;
    }

    // Initialize as self-referential (for headers)
    void init_as_header(int32_t id) {
        left = right = up = down = this;
        column = this;
        column_id = id;
        size = 0;
        piece_index = -1;
        position = -1;
        rotation = 0;
    }

    // Initialize as regular node
    void init_as_node(int16_t piece, int16_t pos, int8_t rot, size_t rid = 0) {
        piece_index = piece;
        position = pos;
        rotation = rot;
        row_id = rid;
        column_id = -1;
        size = 0;
    }
};

/**
 * @brief Row metadata for edge compatibility checking
 *
 * Stores precomputed edge values for O(1) edge compatibility checks
 * during the hybrid DLX + edge propagation search.
 */
struct RowMetadata {
    int16_t piece_index;
    int16_t position;
    int8_t rotation;

    // Precomputed rotated edges
    uint16_t edge_up;
    uint16_t edge_right;
    uint16_t edge_down;
    uint16_t edge_left;

    // Row ID for quick lookup
    size_t row_id;

    // LCV score: higher = less constraining = try first
    // Computed as sum of color frequencies for non-WALL edges
    int16_t lcv_score = 0;

    // Get edge by direction (0=UP, 1=RIGHT, 2=DOWN, 3=LEFT)
    [[gnu::always_inline]] uint16_t get_edge(int direction) const {
        switch (direction) {
            case 0: return edge_up;
            case 1: return edge_right;
            case 2: return edge_down;
            case 3: return edge_left;
            default: return 0;
        }
    }
};

/**
 * @brief Column type enumeration
 */
enum class ColumnType : uint8_t {
    PIECE = 0,      // Piece usage column (0 to num_pieces-1)
    POSITION = 1    // Position filled column (num_pieces to num_pieces + num_positions - 1)
};

/**
 * @brief Position type for border-first heuristic
 *
 * Priority order: CORNER > EDGE > INTERIOR
 * - Corners have 2 wall edges, only 1 valid rotation
 * - Edges have 1 wall edge, 2 valid rotations
 * - Interior has 0 wall edges, 4 valid rotations
 */
enum class PositionType : uint8_t {
    CORNER = 0,     // 4 corners: highest priority (most constrained)
    EDGE = 1,       // 56 edges for 16x16: medium priority
    INTERIOR = 2    // 196 interior for 16x16: lowest priority
};

/**
 * @brief Get column type from column ID
 */
[[gnu::always_inline]] inline ColumnType get_column_type(int32_t column_id, size_t num_pieces) {
    return (column_id < static_cast<int32_t>(num_pieces)) ? ColumnType::PIECE : ColumnType::POSITION;
}

/**
 * @brief Get piece index from piece column ID
 */
[[gnu::always_inline]] inline int get_piece_from_column(int32_t column_id) {
    return column_id;
}

/**
 * @brief Get position from position column ID
 */
[[gnu::always_inline]] inline int get_position_from_column(int32_t column_id, size_t num_pieces) {
    return column_id - static_cast<int32_t>(num_pieces);
}

} // namespace eternity2_v3

#endif // ETERNITY2_V3_DLX_NODE_H
