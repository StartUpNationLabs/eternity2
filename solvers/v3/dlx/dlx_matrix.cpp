//
// Dancing Links Matrix Implementation
//

#include "dlx_matrix.h"
#include "common/piece_utils.h"
#include <limits>
#include <algorithm>

namespace eternity2_v3 {

DLXMatrix::DLXMatrix(size_t board_size, const std::vector<Piece>& pieces)
    : board_size_(board_size)
    , num_positions_(board_size * board_size)
    , num_columns_(pieces.size() + num_positions_)
    , pieces_(pieces)
    , uses_shared_metadata_(false)
{
    // Pre-allocate storage with generous estimate to avoid reallocation
    // Max possible: each piece can go in each position with each rotation
    // Actual will be less due to border constraints
    size_t max_rows = pieces_.size() * num_positions_ * 4;
    size_t max_nodes = max_rows * 2;  // 2 nodes per row (piece + position)

    column_headers_.reserve(num_columns_);
    nodes_.reserve(max_nodes);
    row_metadata_.reserve(max_rows);
    row_starts_.reserve(max_rows);

    // Initialize arrays
    position_types_.fill(PositionType::INTERIOR);
    color_frequency_.fill(0);

    // Precompute position types and color frequencies
    precompute_position_types();
    compute_color_frequencies();
}

DLXMatrix::DLXMatrix(size_t board_size, const std::vector<Piece>& pieces,
                     const std::vector<RowMetadata>& shared_row_metadata)
    : board_size_(board_size)
    , num_positions_(board_size * board_size)
    , num_columns_(pieces.size() + num_positions_)
    , pieces_(pieces)
    , shared_row_metadata_(&shared_row_metadata)  // Store pointer to shared metadata
    , uses_shared_metadata_(true)
{
    // Pre-allocate storage for nodes based on shared metadata size
    size_t num_rows = shared_row_metadata.size();
    size_t max_nodes = num_rows * 2;  // 2 nodes per row (piece + position)

    column_headers_.reserve(num_columns_);
    nodes_.reserve(max_nodes);
    row_starts_.reserve(num_rows);

    // Initialize arrays
    position_types_.fill(PositionType::INTERIOR);
    color_frequency_.fill(0);

    // Precompute position types and color frequencies
    precompute_position_types();
    compute_color_frequencies();
}

void DLXMatrix::create_column_headers() {
    column_headers_.resize(num_columns_);

    // Initialize root
    root_.init_as_header(-1);

    // Create column headers and link them
    DLXNode* prev = &root_;

    for (size_t i = 0; i < num_columns_; ++i) {
        column_headers_[i].init_as_header(static_cast<int32_t>(i));

        // Link horizontally
        prev->right = &column_headers_[i];
        column_headers_[i].left = prev;

        prev = &column_headers_[i];
    }

    // Close the circular list
    prev->right = &root_;
    root_.left = prev;
}

bool DLXMatrix::is_valid_placement(size_t piece_idx, size_t position, int rotation) const {
    size_t x = get_x(position);
    size_t y = get_y(position);

    Piece rotated = rotate_piece_right(pieces_[piece_idx], rotation);

    PiecePart edge_up = get_piece_part(rotated, UP_MASK);
    PiecePart edge_right = get_piece_part(rotated, RIGHT_MASK);
    PiecePart edge_down = get_piece_part(rotated, DOWN_MASK);
    PiecePart edge_left = get_piece_part(rotated, LEFT_MASK);

    // Border constraints
    bool is_top_border = (y == 0);
    bool is_right_border = (x == board_size_ - 1);
    bool is_bottom_border = (y == board_size_ - 1);
    bool is_left_border = (x == 0);

    // Border positions must have WALL edges
    if (is_top_border && edge_up != WALL) return false;
    if (is_right_border && edge_right != WALL) return false;
    if (is_bottom_border && edge_down != WALL) return false;
    if (is_left_border && edge_left != WALL) return false;

    // Interior edges must NOT be WALL
    if (!is_top_border && edge_up == WALL) return false;
    if (!is_right_border && edge_right == WALL) return false;
    if (!is_bottom_border && edge_down == WALL) return false;
    if (!is_left_border && edge_left == WALL) return false;

    return true;
}

void DLXMatrix::add_row(size_t piece_idx, size_t position, int rotation) {
    size_t row_id = row_metadata_.size();

    // Compute rotated piece and edges
    Piece rotated = rotate_piece_right(pieces_[piece_idx], rotation);

    // Create row metadata
    RowMetadata meta;
    meta.piece_index = static_cast<int16_t>(piece_idx);
    meta.position = static_cast<int16_t>(position);
    meta.rotation = static_cast<int8_t>(rotation);
    meta.edge_up = get_piece_part(rotated, UP_MASK);
    meta.edge_right = get_piece_part(rotated, RIGHT_MASK);
    meta.edge_down = get_piece_part(rotated, DOWN_MASK);
    meta.edge_left = get_piece_part(rotated, LEFT_MASK);
    meta.row_id = row_id;

    // Compute LCV score: sum of color frequencies for non-WALL edges
    // Higher score = more common colors = less constraining = try first
    int16_t lcv = 0;
    if (meta.edge_up != WALL && meta.edge_up < MAX_COLORS) {
        lcv += static_cast<int16_t>(color_frequency_[meta.edge_up]);
    }
    if (meta.edge_right != WALL && meta.edge_right < MAX_COLORS) {
        lcv += static_cast<int16_t>(color_frequency_[meta.edge_right]);
    }
    if (meta.edge_down != WALL && meta.edge_down < MAX_COLORS) {
        lcv += static_cast<int16_t>(color_frequency_[meta.edge_down]);
    }
    if (meta.edge_left != WALL && meta.edge_left < MAX_COLORS) {
        lcv += static_cast<int16_t>(color_frequency_[meta.edge_left]);
    }
    meta.lcv_score = lcv;

    row_metadata_.push_back(meta);

    // Create nodes for this row
    // Node 1: piece column
    size_t piece_col = piece_idx;
    nodes_.emplace_back();
    DLXNode* piece_node = &nodes_.back();
    piece_node->init_as_node(static_cast<int16_t>(piece_idx),
                              static_cast<int16_t>(position),
                              static_cast<int8_t>(rotation),
                              row_id);

    // Node 2: position column
    size_t pos_col = pieces_.size() + position;
    nodes_.emplace_back();
    DLXNode* pos_node = &nodes_.back();
    pos_node->init_as_node(static_cast<int16_t>(piece_idx),
                            static_cast<int16_t>(position),
                            static_cast<int8_t>(rotation),
                            row_id);

    // Link nodes to their columns
    link_node_to_column(piece_node, &column_headers_[piece_col]);
    link_node_to_column(pos_node, &column_headers_[pos_col]);

    // Link nodes horizontally (circular)
    piece_node->left = pos_node;
    piece_node->right = pos_node;
    pos_node->left = piece_node;
    pos_node->right = piece_node;

    // Store row start
    row_starts_.push_back(piece_node);
}

void DLXMatrix::link_node_to_column(DLXNode* node, DLXNode* column) {
    node->column = column;

    // Insert at bottom of column
    node->up = column->up;
    node->down = column;
    column->up->down = node;
    column->up = node;

    // Increment column size
    column->size++;
}

void DLXMatrix::build_matrix() {
    create_column_headers();

    if (uses_shared_metadata_ && shared_row_metadata_ != nullptr) {
        // Rebuild matrix structure using existing shared metadata
        // This is much faster than rebuilding from scratch
        // (No logging here - logging is handled by caller)
        for (size_t row_id = 0; row_id < shared_row_metadata_->size(); ++row_id) {
            const RowMetadata& meta = (*shared_row_metadata_)[row_id];
            
            // Create nodes for this row
            // Node 1: piece column
            size_t piece_col = static_cast<size_t>(meta.piece_index);
            nodes_.emplace_back();
            DLXNode* piece_node = &nodes_.back();
            piece_node->init_as_node(meta.piece_index, meta.position, meta.rotation, row_id);

            // Node 2: position column
            size_t pos_col = pieces_.size() + static_cast<size_t>(meta.position);
            nodes_.emplace_back();
            DLXNode* pos_node = &nodes_.back();
            pos_node->init_as_node(meta.piece_index, meta.position, meta.rotation, row_id);

            // Link nodes to their columns
            link_node_to_column(piece_node, &column_headers_[piece_col]);
            link_node_to_column(pos_node, &column_headers_[pos_col]);

            // Link nodes horizontally (circular)
            piece_node->left = pos_node;
            piece_node->right = pos_node;
            pos_node->left = piece_node;
            pos_node->right = piece_node;

            // Store row start
            row_starts_.push_back(piece_node);
        }
    } else {
        // Generate all valid placement rows
        for (size_t piece_idx = 0; piece_idx < pieces_.size(); ++piece_idx) {
            for (size_t position = 0; position < num_positions_; ++position) {
                for (int rotation = 0; rotation < 4; ++rotation) {
                    if (is_valid_placement(piece_idx, position, rotation)) {
                        add_row(piece_idx, position, rotation);
                    }
                }
            }
        }
    }
}

void DLXMatrix::build_from_partial(const Board& partial_board) {
    // Build the matrix structure (using shared metadata if available)
    build_matrix();

    // Then cover columns for pre-placed pieces
    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index idx = {x, y};
            const RotatedPiece* piece = get_piece(partial_board, idx);

            // Check if position has a placed piece
            if (piece != nullptr && piece->piece != EMPTY && piece->piece != 0) {
                size_t position = get_position(x, y);

                // Cover the piece column
                cover(&column_headers_[piece->index]);

                // Cover the position column
                cover(&column_headers_[pieces_.size() + position]);
            }
        }
    }
}

void DLXMatrix::cover(DLXNode* column) {
    // Remove column from header list
    column->right->left = column->left;
    column->left->right = column->right;

    // For each row in this column
    for (DLXNode* row = column->down; row != column; row = row->down) {
        // Remove all other nodes in this row from their columns
        for (DLXNode* node = row->right; node != row; node = node->right) {
            node->down->up = node->up;
            node->up->down = node->down;
            node->column->size--;
        }
    }
}

void DLXMatrix::uncover(DLXNode* column) {
    // Restore in reverse order of cover
    for (DLXNode* row = column->up; row != column; row = row->up) {
        for (DLXNode* node = row->left; node != row; node = node->left) {
            node->column->size++;
            node->down->up = node;
            node->up->down = node;
        }
    }

    // Restore column to header list
    column->right->left = column;
    column->left->right = column;
}

DLXNode* DLXMatrix::choose_column() {
    DLXNode* best = nullptr;
    int min_size = std::numeric_limits<int>::max();

    for (DLXNode* col = root_.right; col != &root_; col = col->right) {
        if (col->size < min_size) {
            min_size = col->size;
            best = col;

            // Early exit for size 0 or 1 (can't do better)
            if (min_size <= 1) {
                break;
            }
        }
    }

    return best;
}

const RowMetadata& DLXMatrix::get_row_metadata(const DLXNode* node) const {
    // O(1) lookup using row_id stored in node
    if (uses_shared_metadata_ && shared_row_metadata_ != nullptr) {
        return (*shared_row_metadata_)[node->row_id];
    }
    return row_metadata_[node->row_id];
}

void DLXMatrix::cover_row(DLXNode* row_node) {
    // Remove all nodes in this row from their columns (vertical links only)
    // Don't touch the column header's horizontal links
    DLXNode* node = row_node;
    do {
        node->down->up = node->up;
        node->up->down = node->down;
        node->column->size--;
        node = node->right;
    } while (node != row_node);
}

void DLXMatrix::uncover_row(DLXNode* row_node) {
    // Restore all nodes in this row to their columns (reverse order of cover)
    DLXNode* node = row_node;
    do {
        node = node->left;  // Move first (reverse order)
        node->column->size++;
        node->down->up = node;
        node->up->down = node;
    } while (node != row_node);
}

void DLXMatrix::precompute_position_types() {
    for (size_t pos = 0; pos < num_positions_; ++pos) {
        size_t x = get_x(pos);
        size_t y = get_y(pos);

        bool is_x_border = (x == 0 || x == board_size_ - 1);
        bool is_y_border = (y == 0 || y == board_size_ - 1);

        if (is_x_border && is_y_border) {
            position_types_[pos] = PositionType::CORNER;
        } else if (is_x_border || is_y_border) {
            position_types_[pos] = PositionType::EDGE;
        } else {
            position_types_[pos] = PositionType::INTERIOR;
        }
    }
}

void DLXMatrix::compute_color_frequencies() {
    // Count frequency of each color across all pieces and edges
    for (const auto& piece : pieces_) {
        uint16_t up = get_piece_part(piece, UP_MASK);
        uint16_t right = get_piece_part(piece, RIGHT_MASK);
        uint16_t down = get_piece_part(piece, DOWN_MASK);
        uint16_t left = get_piece_part(piece, LEFT_MASK);

        // Only count non-WALL edges (WALL = 0)
        if (up != WALL && up < MAX_COLORS) color_frequency_[up]++;
        if (right != WALL && right < MAX_COLORS) color_frequency_[right]++;
        if (down != WALL && down < MAX_COLORS) color_frequency_[down]++;
        if (left != WALL && left < MAX_COLORS) color_frequency_[left]++;
    }
}

DLXNode* DLXMatrix::choose_column_smart() {
    DLXNode* best = nullptr;
    int best_score = std::numeric_limits<int>::max();

    for (DLXNode* col = root_.right; col != &root_; col = col->right) {
        int32_t col_id = col->column_id;
        int score;

        // Dead end check - return immediately
        if (col->size == 0) {
            return col;
        }

        if (col_id < static_cast<int32_t>(pieces_.size())) {
            // Piece column: lowest priority (use large base score)
            // S-heuristic as tiebreaker
            score = 10000 + col->size;
        } else {
            // Position column: prioritize by position type
            size_t position = static_cast<size_t>(col_id - static_cast<int32_t>(pieces_.size()));
            PositionType pos_type = position_types_[position];

            // Priority weights: CORNER (0) > EDGE (1) > INTERIOR (2)
            // Each type tier is separated by 1000 to ensure strict ordering
            int type_weight = static_cast<int>(pos_type) * 1000;

            // Within same type: prefer smaller domain (S-heuristic)
            score = type_weight + col->size;
        }

        if (score < best_score) {
            best_score = score;
            best = col;

            // Early exit if we found a size-1 corner position
            if (col->size == 1 && best_score < 1000) {
                break;
            }
        }
    }

    return best;
}

} // namespace eternity2_v3
