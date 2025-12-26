//
// Domain Manager Implementation
// Maintaining Arc Consistency (MAC) for Eternity II Solver v2
//

#include "domain.h"

using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::UP_MASK;
using eternity2_common::RIGHT_MASK;
using eternity2_common::DOWN_MASK;
using eternity2_common::LEFT_MASK;
using eternity2_common::WALL;
using eternity2_common::rotate_piece_right;
using eternity2_common::get_piece_part;
#include <algorithm>

namespace eternity2_v2 {

// Direction constants for neighbor access
constexpr int DIR_UP = 0;
constexpr int DIR_RIGHT = 1;
constexpr int DIR_DOWN = 2;
constexpr int DIR_LEFT = 3;

// Opposite direction mapping
constexpr int opposite_direction(int dir) {
    return (dir + 2) % 4;
}

DomainManager::DomainManager(size_t board_size, const std::vector<Piece>& pieces)
    : board_size_(board_size)
    , pieces_(pieces)
    , domains_(board_size * board_size)
{
    // Initialize all pieces as available using bitset
    piece_availability_.set();  // Set all bits to 1

    // Reserve space for trail to avoid reallocations
    trail_.reserve(board_size * board_size * 10);  // Estimate ~10 entries per placed piece
    choice_points_.reserve(board_size * board_size);
}

void DomainManager::initialize_domains() {
    // Precompute piece compatibility matrix for O(1) constraint lookups
    if (!compatibility_computed_) {
        precompute_compatibility();
        compatibility_computed_ = true;
    }

    // Reset piece availability - all pieces available
    piece_availability_.set();
    // Clear bits for pieces beyond our actual piece count
    for (size_t i = pieces_.size(); i < MAX_PIECES; ++i) {
        piece_availability_.reset(i);
    }

    // Clear trail and choice points
    trail_.clear();
    choice_points_.clear();

    // Initialize domain for each position based on position type (corner, edge, interior)
    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index index = {x, y};
            domains_[to_1d(index)].valid_pieces = compute_initial_domain(index);
            domains_[to_1d(index)].is_assigned = false;
        }
    }
    assigned_count_ = 0;
}

const DomainEntry& DomainManager::get_domain(Index index) const {
    return domains_[to_1d(index)];
}

DomainEntry& DomainManager::get_domain_mut(Index index) {
    return domains_[to_1d(index)];
}

size_t DomainManager::get_domain_size(Index index) const {
    return domains_[to_1d(index)].size();
}

bool DomainManager::place_piece(Index index, const RotatedPiece& piece) {
    size_t idx = to_1d(index);

    // Record position assignment in trail
    record_position_assigned(idx);

    // Record domain shrink: all pieces except the one being placed are "removed"
    // This is needed so we can restore the domain on backtrack
    std::vector<RotatedPiece> removed;
    for (const auto& rp : domains_[idx].valid_pieces) {
        if (rp.index != piece.index || rp.rotation != piece.rotation) {
            removed.push_back(rp);
        }
    }
    record_domain_shrink(idx, removed);

    // Mark position as assigned
    domains_[idx].is_assigned = true;
    domains_[idx].valid_pieces.clear();
    domains_[idx].valid_pieces.push_back(piece);
    assigned_count_++;

    // Record piece used in trail
    record_piece_used(piece.index);

    // Mark piece as used (using bitset)
    piece_availability_.reset(piece.index);

    // Propagate constraints to neighbors
    return propagate_to_neighbors(index, piece);
}

void DomainManager::remove_piece(Index index) {
    size_t idx = to_1d(index);

    // Get the piece that was placed (should be single entry)
    if (!domains_[idx].valid_pieces.empty()) {
        int piece_index = domains_[idx].valid_pieces[0].index;
        piece_availability_.set(piece_index);  // Using bitset
    }

    domains_[idx].is_assigned = false;
    assigned_count_--;

    // Note: Full domain restoration happens via pop_state()
}

bool DomainManager::is_piece_available(int piece_index) const {
    return piece_availability_.test(piece_index);  // Using bitset
}

void DomainManager::mark_piece_used(int piece_index) {
    piece_availability_.reset(piece_index);  // Using bitset
}

void DomainManager::mark_piece_available(int piece_index) {
    piece_availability_.set(piece_index);  // Using bitset
}

void DomainManager::push_state() {
    // Simply record current trail position as a choice point
    choice_points_.push_back(trail_.size());
}

void DomainManager::pop_state() {
    if (choice_points_.empty()) {
        return;
    }

    size_t restore_point = choice_points_.back();
    choice_points_.pop_back();

    // Undo all trail entries back to the choice point (in reverse order)
    while (trail_.size() > restore_point) {
        undo_trail_entry(trail_.back());
        trail_.pop_back();
    }
}

void DomainManager::undo_trail_entry(const TrailEntry& entry) {
    switch (entry.type) {
        case TrailEntry::Type::DOMAIN_SHRINK:
            // Restore removed pieces to domain
            {
                auto& domain = domains_[entry.position_1d];
                domain.valid_pieces.insert(
                    domain.valid_pieces.end(),
                    entry.removed_pieces.begin(),
                    entry.removed_pieces.end()
                );
            }
            break;

        case TrailEntry::Type::PIECE_USED:
            // Mark piece as available again
            piece_availability_.set(entry.piece_index);
            break;

        case TrailEntry::Type::POSITION_ASSIGNED:
            // Mark position as unassigned
            domains_[entry.position_1d].is_assigned = false;
            assigned_count_--;
            break;
    }
}

void DomainManager::record_domain_shrink(size_t position_1d, const std::vector<RotatedPiece>& removed) {
    if (!removed.empty()) {
        trail_.push_back({
            TrailEntry::Type::DOMAIN_SHRINK,
            position_1d,
            -1,  // Not used for DOMAIN_SHRINK
            removed
        });
    }
}

void DomainManager::record_piece_used(int piece_index) {
    trail_.push_back({
        TrailEntry::Type::PIECE_USED,
        0,  // Not used for PIECE_USED
        piece_index,
        {}  // No removed pieces
    });
}

void DomainManager::record_position_assigned(size_t position_1d) {
    trail_.push_back({
        TrailEntry::Type::POSITION_ASSIGNED,
        position_1d,
        -1,  // Not used for POSITION_ASSIGNED
        {}   // No removed pieces
    });
}

std::vector<Index> DomainManager::get_unassigned_positions() const {
    std::vector<Index> unassigned;
    unassigned.reserve(total_positions() - assigned_count_);

    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index index = {x, y};
            if (!domains_[to_1d(index)].is_assigned) {
                unassigned.push_back(index);
            }
        }
    }
    return unassigned;
}

std::vector<Index> DomainManager::get_neighbor_indices(Index index) const {
    std::vector<Index> neighbors;
    neighbors.reserve(4);

    // Up
    if (index.second > 0) {
        neighbors.push_back({index.first, index.second - 1});
    }
    // Right
    if (index.first < board_size_ - 1) {
        neighbors.push_back({index.first + 1, index.second});
    }
    // Down
    if (index.second < board_size_ - 1) {
        neighbors.push_back({index.first, index.second + 1});
    }
    // Left
    if (index.first > 0) {
        neighbors.push_back({index.first - 1, index.second});
    }

    return neighbors;
}

size_t DomainManager::count_unassigned_neighbors(Index index) const {
    size_t count = 0;

    // Up
    if (index.second > 0) {
        if (!domains_[to_1d({index.first, index.second - 1})].is_assigned) count++;
    }
    // Right
    if (index.first < board_size_ - 1) {
        if (!domains_[to_1d({index.first + 1, index.second})].is_assigned) count++;
    }
    // Down
    if (index.second < board_size_ - 1) {
        if (!domains_[to_1d({index.first, index.second + 1})].is_assigned) count++;
    }
    // Left
    if (index.first > 0) {
        if (!domains_[to_1d({index.first - 1, index.second})].is_assigned) count++;
    }

    return count;
}

bool DomainManager::is_complete() const {
    return assigned_count_ == total_positions();
}

size_t DomainManager::to_1d(Index index) const {
    return index.second * board_size_ + index.first;
}

Index DomainManager::to_2d(size_t index) const {
    return {index % board_size_, index / board_size_};
}

bool DomainManager::is_valid_index(Index index) const {
    return index.first < board_size_ && index.second < board_size_;
}

bool DomainManager::is_corner(Index index) const {
    bool x_edge = (index.first == 0 || index.first == board_size_ - 1);
    bool y_edge = (index.second == 0 || index.second == board_size_ - 1);
    return x_edge && y_edge;
}

bool DomainManager::is_edge(Index index) const {
    bool x_edge = (index.first == 0 || index.first == board_size_ - 1);
    bool y_edge = (index.second == 0 || index.second == board_size_ - 1);
    return (x_edge || y_edge) && !is_corner(index);
}

bool DomainManager::is_interior(Index index) const {
    return !is_corner(index) && !is_edge(index);
}

std::vector<RotatedPiece> DomainManager::compute_initial_domain(Index index) const {
    std::vector<RotatedPiece> domain;
    domain.reserve(pieces_.size() * 4);  // Worst case: all pieces in all rotations

    // Determine which edges must be walls based on position
    bool need_wall_up = (index.second == 0);
    bool need_wall_right = (index.first == board_size_ - 1);
    bool need_wall_down = (index.second == board_size_ - 1);
    bool need_wall_left = (index.first == 0);

    // Determine which edges must NOT be walls (interior edges)
    bool no_wall_up = (index.second > 0);
    bool no_wall_right = (index.first < board_size_ - 1);
    bool no_wall_down = (index.second < board_size_ - 1);
    bool no_wall_left = (index.first > 0);

    // Check each piece in each rotation
    for (size_t i = 0; i < pieces_.size(); ++i) {
        for (int rot = 0; rot < 4; ++rot) {
            Piece rotated = rotate_piece_right(pieces_[i], rot);

            PiecePart up_part = get_piece_part(rotated, UP_MASK);
            PiecePart right_part = get_piece_part(rotated, RIGHT_MASK);
            PiecePart down_part = get_piece_part(rotated, DOWN_MASK);
            PiecePart left_part = get_piece_part(rotated, LEFT_MASK);

            // Check wall constraints
            bool valid = true;

            // Must have wall on border edges
            if (need_wall_up && up_part != WALL) valid = false;
            if (need_wall_right && right_part != WALL) valid = false;
            if (need_wall_down && down_part != WALL) valid = false;
            if (need_wall_left && left_part != WALL) valid = false;

            // Must NOT have wall on interior edges
            if (no_wall_up && up_part == WALL) valid = false;
            if (no_wall_right && right_part == WALL) valid = false;
            if (no_wall_down && down_part == WALL) valid = false;
            if (no_wall_left && left_part == WALL) valid = false;

            if (valid) {
                domain.push_back({pieces_[i], rot, static_cast<int>(i)});
            }
        }
    }

    return domain;
}

PiecePart DomainManager::get_edge_constraint(const RotatedPiece& piece, int direction) const {
    Piece rotated = rotate_piece_right(piece.piece, piece.rotation);

    switch (direction) {
        case DIR_UP:
            return get_piece_part(rotated, UP_MASK);
        case DIR_RIGHT:
            return get_piece_part(rotated, RIGHT_MASK);
        case DIR_DOWN:
            return get_piece_part(rotated, DOWN_MASK);
        case DIR_LEFT:
            return get_piece_part(rotated, LEFT_MASK);
        default:
            return EMPTY;
    }
}

void DomainManager::filter_domain_by_constraint(Index index, int direction, PiecePart constraint) {
    size_t idx = to_1d(index);
    DomainEntry& domain = domains_[idx];

    if (domain.is_assigned) return;  // Don't filter assigned positions

    // Determine which mask to use for this direction
    Piece mask;
    switch (direction) {
        case DIR_UP:    mask = UP_MASK; break;
        case DIR_RIGHT: mask = RIGHT_MASK; break;
        case DIR_DOWN:  mask = DOWN_MASK; break;
        case DIR_LEFT:  mask = LEFT_MASK; break;
        default: return;
    }

    // Collect pieces to remove (for trail)
    std::vector<RotatedPiece> removed;

    // Filter out pieces that don't match the constraint
    auto it = std::remove_if(domain.valid_pieces.begin(), domain.valid_pieces.end(),
        [&](const RotatedPiece& rp) {
            // Check if this piece is still available (using bitset)
            if (!piece_availability_.test(rp.index)) {
                removed.push_back(rp);
                return true;  // Remove unavailable pieces
            }

            Piece rotated = rotate_piece_right(rp.piece, rp.rotation);
            PiecePart edge = get_piece_part(rotated, mask);

            // Edge must match the constraint
            if (edge != constraint) {
                removed.push_back(rp);
                return true;
            }
            return false;
        }
    );

    domain.valid_pieces.erase(it, domain.valid_pieces.end());

    // Record removed pieces in trail for backtracking
    record_domain_shrink(idx, removed);
}

bool DomainManager::propagate_to_neighbors(Index placed_index, const RotatedPiece& placed_piece) {
    // Get edge values from placed piece
    Piece rotated = rotate_piece_right(placed_piece.piece, placed_piece.rotation);
    PiecePart up_edge = get_piece_part(rotated, UP_MASK);
    PiecePart right_edge = get_piece_part(rotated, RIGHT_MASK);
    PiecePart down_edge = get_piece_part(rotated, DOWN_MASK);
    PiecePart left_edge = get_piece_part(rotated, LEFT_MASK);

    // Propagate to up neighbor (they need matching DOWN edge)
    if (placed_index.second > 0) {
        Index up_idx = {placed_index.first, placed_index.second - 1};
        if (!domains_[to_1d(up_idx)].is_assigned) {
            filter_domain_by_constraint(up_idx, DIR_DOWN, up_edge);
            if (domains_[to_1d(up_idx)].empty()) return false;
        }
    }

    // Propagate to right neighbor (they need matching LEFT edge)
    if (placed_index.first < board_size_ - 1) {
        Index right_idx = {placed_index.first + 1, placed_index.second};
        if (!domains_[to_1d(right_idx)].is_assigned) {
            filter_domain_by_constraint(right_idx, DIR_LEFT, right_edge);
            if (domains_[to_1d(right_idx)].empty()) return false;
        }
    }

    // Propagate to down neighbor (they need matching UP edge)
    if (placed_index.second < board_size_ - 1) {
        Index down_idx = {placed_index.first, placed_index.second + 1};
        if (!domains_[to_1d(down_idx)].is_assigned) {
            filter_domain_by_constraint(down_idx, DIR_UP, down_edge);
            if (domains_[to_1d(down_idx)].empty()) return false;
        }
    }

    // Propagate to left neighbor (they need matching RIGHT edge)
    if (placed_index.first > 0) {
        Index left_idx = {placed_index.first - 1, placed_index.second};
        if (!domains_[to_1d(left_idx)].is_assigned) {
            filter_domain_by_constraint(left_idx, DIR_RIGHT, left_edge);
            if (domains_[to_1d(left_idx)].empty()) return false;
        }
    }

    // Also filter out the used piece from all other domains
    for (size_t i = 0; i < domains_.size(); ++i) {
        if (domains_[i].is_assigned) continue;

        auto& valid = domains_[i].valid_pieces;
        std::vector<RotatedPiece> removed;

        auto it = std::remove_if(valid.begin(), valid.end(),
            [&](const RotatedPiece& rp) {
                if (rp.index == placed_piece.index) {
                    removed.push_back(rp);
                    return true;
                }
                return false;
            }
        );
        valid.erase(it, valid.end());

        // Record domain shrink in trail
        record_domain_shrink(i, removed);

        if (valid.empty()) return false;
    }

    return true;
}

void DomainManager::precompute_compatibility() {
    // Initialize the compatibility matrix
    compatible_.resize(pieces_.size());
    for (size_t i = 0; i < pieces_.size(); ++i) {
        for (int r1 = 0; r1 < 4; ++r1) {
            for (int dir = 0; dir < 4; ++dir) {
                compatible_[i][r1][dir].clear();
            }
        }
    }

    // For each piece and rotation, compute compatible pieces for each direction
    for (size_t i = 0; i < pieces_.size(); ++i) {
        for (int r1 = 0; r1 < 4; ++r1) {
            Piece rotated1 = rotate_piece_right(pieces_[i], r1);

            // Get edges for this piece/rotation
            PiecePart up_edge = get_piece_part(rotated1, UP_MASK);
            PiecePart right_edge = get_piece_part(rotated1, RIGHT_MASK);
            PiecePart down_edge = get_piece_part(rotated1, DOWN_MASK);
            PiecePart left_edge = get_piece_part(rotated1, LEFT_MASK);

            // Find compatible pieces for each direction
            for (size_t j = 0; j < pieces_.size(); ++j) {
                if (i == j) continue;  // Same piece can't be adjacent to itself

                for (int r2 = 0; r2 < 4; ++r2) {
                    Piece rotated2 = rotate_piece_right(pieces_[j], r2);

                    // Check UP direction (neighbor needs matching DOWN edge)
                    if (up_edge == get_piece_part(rotated2, DOWN_MASK)) {
                        compatible_[i][r1][DIR_UP].push_back({static_cast<int>(j), r2});
                    }

                    // Check RIGHT direction (neighbor needs matching LEFT edge)
                    if (right_edge == get_piece_part(rotated2, LEFT_MASK)) {
                        compatible_[i][r1][DIR_RIGHT].push_back({static_cast<int>(j), r2});
                    }

                    // Check DOWN direction (neighbor needs matching UP edge)
                    if (down_edge == get_piece_part(rotated2, UP_MASK)) {
                        compatible_[i][r1][DIR_DOWN].push_back({static_cast<int>(j), r2});
                    }

                    // Check LEFT direction (neighbor needs matching RIGHT edge)
                    if (left_edge == get_piece_part(rotated2, RIGHT_MASK)) {
                        compatible_[i][r1][DIR_LEFT].push_back({static_cast<int>(j), r2});
                    }
                }
            }
        }
    }
}

bool DomainManager::recompute_domain(Index index, const RotatedPiece& placed_piece, Index placed_index) {
    // This is called when we need to filter based on a newly placed neighbor
    // Determine the direction from index to placed_index

    int dir_to_placed = -1;
    if (placed_index.second == index.second - 1) dir_to_placed = DIR_UP;
    else if (placed_index.first == index.first + 1) dir_to_placed = DIR_RIGHT;
    else if (placed_index.second == index.second + 1) dir_to_placed = DIR_DOWN;
    else if (placed_index.first == index.first - 1) dir_to_placed = DIR_LEFT;
    else return true;  // Not a neighbor

    // Get the constraint (the edge of the placed piece facing us)
    int opposite_dir = opposite_direction(dir_to_placed);
    PiecePart constraint = get_edge_constraint(placed_piece, opposite_dir);

    // Filter our domain
    filter_domain_by_constraint(index, dir_to_placed, constraint);

    return !domains_[to_1d(index)].empty();
}

} // namespace eternity2_v2
