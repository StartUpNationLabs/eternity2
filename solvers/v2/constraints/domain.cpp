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

    // OPTIMIZATION: Pre-allocate scratch buffers to avoid hot-path heap allocations
    // Typical domain size is pieces * 4 rotations, but filtering removes most
    scratch_removed_.reserve(pieces.size() * 4);
    scratch_removed_propagate_.reserve(16);  // Usually only a few pieces removed per domain
}

void DomainManager::initialize_domains() {
    // Reset piece availability - all pieces available
    piece_availability_.set();
    // Clear bits for pieces beyond our actual piece count
    for (size_t i = pieces_.size(); i < MAX_PIECES; ++i) {
        piece_availability_.reset(i);
    }

    // OPTIMIZATION: Compute color frequency for rare color heuristic
    color_frequency_.fill(0);
    max_color_frequency_ = 0;
    for (const auto& piece : pieces_) {
        // Count each edge color (4 edges per piece)
        PiecePart up = get_piece_part(piece, UP_MASK);
        PiecePart right = get_piece_part(piece, RIGHT_MASK);
        PiecePart down = get_piece_part(piece, DOWN_MASK);
        PiecePart left = get_piece_part(piece, LEFT_MASK);
        if (up < MAX_COLORS) color_frequency_[up]++;
        if (right < MAX_COLORS) color_frequency_[right]++;
        if (down < MAX_COLORS) color_frequency_[down]++;
        if (left < MAX_COLORS) color_frequency_[left]++;
    }
    // Find max for normalization
    for (size_t i = 0; i < MAX_COLORS; ++i) {
        if (color_frequency_[i] > max_color_frequency_) {
            max_color_frequency_ = color_frequency_[i];
        }
    }

    // Clear trail and choice points
    trail_.clear();
    choice_points_.clear();

    // Initialize domain for each position based on position type (corner, edge, interior)
    for (size_t y = 0; y < board_size_; ++y) {
        for (size_t x = 0; x < board_size_; ++x) {
            Index index = {x, y};
            size_t idx = to_1d(index);
            domains_[idx].valid_pieces = compute_initial_domain(index);
            domains_[idx].is_assigned = false;

            // OPTIMIZATION: Compute initial neighbor degrees (valid adjacent positions)
            // Corners: 2, Edges: 3, Interior: 4
            uint8_t degree = 0;
            if (y > 0) degree++;                    // has up neighbor
            if (x < board_size_ - 1) degree++;      // has right neighbor
            if (y < board_size_ - 1) degree++;      // has down neighbor
            if (x > 0) degree++;                    // has left neighbor
            neighbor_degrees_[idx] = degree;
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
    // OPTIMIZATION: Use scratch buffer instead of allocating new vector
    scratch_removed_.clear();
    for (const auto& rp : domains_[idx].valid_pieces) {
        if (rp.index != piece.index || rp.rotation != piece.rotation) {
            scratch_removed_.push_back(rp);
        }
    }
    record_domain_shrink(idx, scratch_removed_);

    // Mark position as assigned
    domains_[idx].is_assigned = true;
    domains_[idx].valid_pieces.clear();
    domains_[idx].valid_pieces.push_back(piece);
    assigned_count_++;

    // OPTIMIZATION: Decrement neighbor degrees for adjacent unassigned positions
    // When this position is assigned, it's no longer an "unassigned neighbor" for its neighbors
    if (index.second > 0) {
        size_t up_idx = to_1d({index.first, index.second - 1});
        if (!domains_[up_idx].is_assigned) neighbor_degrees_[up_idx]--;
    }
    if (index.first < board_size_ - 1) {
        size_t right_idx = to_1d({index.first + 1, index.second});
        if (!domains_[right_idx].is_assigned) neighbor_degrees_[right_idx]--;
    }
    if (index.second < board_size_ - 1) {
        size_t down_idx = to_1d({index.first, index.second + 1});
        if (!domains_[down_idx].is_assigned) neighbor_degrees_[down_idx]--;
    }
    if (index.first > 0) {
        size_t left_idx = to_1d({index.first - 1, index.second});
        if (!domains_[left_idx].is_assigned) neighbor_degrees_[left_idx]--;
    }

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

            // OPTIMIZATION: Restore neighbor degrees for adjacent unassigned positions
            {
                Index index = to_2d(entry.position_1d);
                if (index.second > 0) {
                    size_t up_idx = to_1d({index.first, index.second - 1});
                    if (!domains_[up_idx].is_assigned) neighbor_degrees_[up_idx]++;
                }
                if (index.first < board_size_ - 1) {
                    size_t right_idx = to_1d({index.first + 1, index.second});
                    if (!domains_[right_idx].is_assigned) neighbor_degrees_[right_idx]++;
                }
                if (index.second < board_size_ - 1) {
                    size_t down_idx = to_1d({index.first, index.second + 1});
                    if (!domains_[down_idx].is_assigned) neighbor_degrees_[down_idx]++;
                }
                if (index.first > 0) {
                    size_t left_idx = to_1d({index.first - 1, index.second});
                    if (!domains_[left_idx].is_assigned) neighbor_degrees_[left_idx]++;
                }
            }
            break;
    }
}

void DomainManager::record_domain_shrink(size_t position_1d, const std::vector<RotatedPiece>& removed) {
    if (!removed.empty()) {
        TrailEntry entry;
        entry.type = TrailEntry::Type::DOMAIN_SHRINK;
        entry.position_1d = position_1d;
        entry.piece_index = -1;  // Not used for DOMAIN_SHRINK
        // Reserve capacity to avoid reallocation during copy
        entry.removed_pieces.reserve(removed.size());
        for (const auto& rp : removed) {
            entry.removed_pieces.push_back(rp);
        }
        trail_.push_back(std::move(entry));
    }
}

void DomainManager::record_piece_used(int piece_index) {
    TrailEntry entry;
    entry.type = TrailEntry::Type::PIECE_USED;
    entry.position_1d = 0;  // Not used for PIECE_USED
    entry.piece_index = piece_index;
    // removed_pieces stays empty (default constructed)
    trail_.push_back(std::move(entry));
}

void DomainManager::record_position_assigned(size_t position_1d) {
    TrailEntry entry;
    entry.type = TrailEntry::Type::POSITION_ASSIGNED;
    entry.position_1d = position_1d;
    entry.piece_index = -1;  // Not used for POSITION_ASSIGNED
    // removed_pieces stays empty (default constructed)
    trail_.push_back(std::move(entry));
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
    // OPTIMIZATION: Use cached neighbor degrees (O(1) instead of 4 lookups)
    return neighbor_degrees_[to_1d(index)];
}

bool DomainManager::is_complete() const {
    return assigned_count_ == total_positions();
}

// NOTE: to_1d, to_2d, is_valid_index, is_corner, is_edge, is_interior
// are now inline in domain.h for performance

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
                // Create RotatedPiece with precomputed edges for hot path optimization
                RotatedPiece rp;
                rp.piece = pieces_[i];
                rp.rotation = rot;
                rp.index = static_cast<int>(i);
                // Cache edges to avoid repeated rotation during constraint filtering
                rp.edge_up = up_part;
                rp.edge_right = right_part;
                rp.edge_down = down_part;
                rp.edge_left = left_part;
                domain.push_back(rp);
            }
        }
    }

    return domain;
}

PiecePart DomainManager::get_edge_constraint(const RotatedPiece& piece, int direction) const {
    // OPTIMIZATION: Use cached edges instead of recomputing rotation
    switch (direction) {
        case DIR_UP:    return piece.edge_up;
        case DIR_RIGHT: return piece.edge_right;
        case DIR_DOWN:  return piece.edge_down;
        case DIR_LEFT:  return piece.edge_left;
        default:        return EMPTY;
    }
}

void DomainManager::filter_domain_by_constraint(Index index, int direction, PiecePart constraint) {
    size_t idx = to_1d(index);
    DomainEntry& domain = domains_[idx];

    if (domain.is_assigned) return;  // Don't filter assigned positions

    auto& valid = domain.valid_pieces;
    const size_t n = valid.size();

    if (n == 0) return;

    // OPTIMIZATION: Use scratch buffer instead of allocating new vector
    scratch_removed_.clear();

    // OPTIMIZATION: Explicit loop instead of std::remove_if to avoid lambda overhead
    // Single pass: check both availability and edge match, compact in place
    size_t write_pos = 0;

    // Use function pointer to select edge based on direction (eliminates switch per iteration)
    // This is slightly faster than switch in hot loop due to better branch prediction
    for (size_t i = 0; i < n; ++i) {
        const RotatedPiece& rp = valid[i];

        // Check availability first (likely to short-circuit for used pieces)
        if (__builtin_expect(!piece_availability_.test(rp.index), 0)) {
            scratch_removed_.push_back(rp);
            continue;
        }

        // Check edge match using cached edges
        // OPTIMIZATION: Use pointer arithmetic instead of switch
        // Edges are stored contiguously: edge_up, edge_right, edge_down, edge_left
        const PiecePart* edges = &rp.edge_up;
        PiecePart edge = edges[direction];

        if (edge == constraint) {
            if (write_pos != i) {
                valid[write_pos] = valid[i];
            }
            ++write_pos;
        } else {
            scratch_removed_.push_back(rp);
        }
    }

    // Resize vector to remove filtered elements
    valid.resize(write_pos);

    // Record removed pieces in trail for backtracking
    record_domain_shrink(idx, scratch_removed_);
}

bool DomainManager::propagate_to_neighbors(Index placed_index, const RotatedPiece& placed_piece) {
    // OPTIMIZATION: Use cached edges from placed_piece instead of recomputing
    PiecePart up_edge = placed_piece.edge_up;
    PiecePart right_edge = placed_piece.edge_right;
    PiecePart down_edge = placed_piece.edge_down;
    PiecePart left_edge = placed_piece.edge_left;

    // Propagate to up neighbor (they need matching DOWN edge)
    if (placed_index.second > 0) {
        Index up_idx = {placed_index.first, placed_index.second - 1};
        if (!domains_[to_1d(up_idx)].is_assigned) {
            filter_domain_by_constraint(up_idx, DIR_DOWN, up_edge);
            if (__builtin_expect(domains_[to_1d(up_idx)].empty(), 0)) return false;
        }
    }

    // Propagate to right neighbor (they need matching LEFT edge)
    if (placed_index.first < board_size_ - 1) {
        Index right_idx = {placed_index.first + 1, placed_index.second};
        if (!domains_[to_1d(right_idx)].is_assigned) {
            filter_domain_by_constraint(right_idx, DIR_LEFT, right_edge);
            if (__builtin_expect(domains_[to_1d(right_idx)].empty(), 0)) return false;
        }
    }

    // Propagate to down neighbor (they need matching UP edge)
    if (placed_index.second < board_size_ - 1) {
        Index down_idx = {placed_index.first, placed_index.second + 1};
        if (!domains_[to_1d(down_idx)].is_assigned) {
            filter_domain_by_constraint(down_idx, DIR_UP, down_edge);
            if (__builtin_expect(domains_[to_1d(down_idx)].empty(), 0)) return false;
        }
    }

    // Propagate to left neighbor (they need matching RIGHT edge)
    if (placed_index.first > 0) {
        Index left_idx = {placed_index.first - 1, placed_index.second};
        if (!domains_[to_1d(left_idx)].is_assigned) {
            filter_domain_by_constraint(left_idx, DIR_RIGHT, left_edge);
            if (__builtin_expect(domains_[to_1d(left_idx)].empty(), 0)) return false;
        }
    }

    // Remove the placed piece from all other domains
    // Note: Inverted index approach was tried but hurt performance due to stale entries
    // Simple iteration is fast enough with the other optimizations
    const int piece_idx = placed_piece.index;
    for (size_t i = 0; i < domains_.size(); ++i) {
        if (domains_[i].is_assigned) continue;

        auto& valid = domains_[i].valid_pieces;

        // OPTIMIZATION: Use scratch buffer instead of allocating new vector per domain
        scratch_removed_propagate_.clear();

        auto it = std::remove_if(valid.begin(), valid.end(),
            [&](const RotatedPiece& rp) {
                if (rp.index == piece_idx) {
                    scratch_removed_propagate_.push_back(rp);
                    return true;
                }
                return false;
            }
        );
        valid.erase(it, valid.end());

        // Record domain shrink in trail
        record_domain_shrink(i, scratch_removed_propagate_);

        if (__builtin_expect(valid.empty(), 0)) return false;
    }

    return true;
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
