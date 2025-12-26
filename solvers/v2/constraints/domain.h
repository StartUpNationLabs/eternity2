//
// Domain Manager for Maintaining Arc Consistency (MAC)
// solver_v2 - Optimized Eternity II Solver
//

#ifndef ETERNITY2_V2_DOMAIN_H
#define ETERNITY2_V2_DOMAIN_H

#include "v1/piece_search/piece_search.h"
#include "v1/board/board.h"
#include "common/small_vector.h"

#include <vector>
#include <stack>
#include <bitset>
#include <functional>

using eternity2_common::PiecePart;
using eternity2_common::SmallVector;
#include <array>
#include <unordered_map>

namespace eternity2_v2 {

// Maximum pieces for Eternity II (256 pieces on 16x16 board)
static constexpr size_t MAX_PIECES = 256;

// Trail entry for incremental state management
// Instead of copying entire domain state, we record changes and undo them
// OPTIMIZATION: Uses SmallVector to avoid heap allocation for small domain shrinks
struct TrailEntry {
    enum class Type : uint8_t {  // Use uint8_t to minimize enum size
        DOMAIN_SHRINK,      // Pieces were removed from a domain
        PIECE_USED,         // A piece was marked as used
        POSITION_ASSIGNED   // A position was marked as assigned
    };

    // OPTIMIZATION: Fields ordered by size (largest first) to minimize padding
    // Old order: Type(4) + pad(4) + position_1d(8) + piece_index(4) + pad(4) = 24 bytes overhead
    // New order: position_1d(8) + piece_index(4) + Type(1) + pad(3) = 16 bytes overhead (8 bytes saved)
    size_t position_1d;                        // Affected position (for DOMAIN_SHRINK, POSITION_ASSIGNED)
    int piece_index;                           // Affected piece index (for PIECE_USED)
    Type type;
    // SmallVector with inline storage for 8 pieces - balance between inline storage and struct size
    SmallVector<RotatedPiece, 8> removed_pieces;
};

// Domain entry for a single board position
struct DomainEntry {
    std::vector<RotatedPiece> valid_pieces;  // Valid piece/rotation combinations
    bool is_assigned = false;                 // Whether this position has a placed piece

    size_t size() const { return valid_pieces.size(); }
    bool empty() const { return valid_pieces.empty(); }
};


// Snapshot of domains for backtracking (legacy - kept for compatibility)
// Now just stores trail position for efficient undo
struct DomainSnapshot {
    size_t trail_position;  // Position in trail to restore to
};

// Domain Manager - Core component for MAC
// Tracks valid pieces for each position and propagates constraints
class DomainManager {
public:
    DomainManager(size_t board_size, const std::vector<Piece>& pieces);

    // Initialize all domains based on board constraints (corners, edges, interior)
    void initialize_domains();

    // Get domain for a specific position
    const DomainEntry& get_domain(Index index) const;
    DomainEntry& get_domain_mut(Index index);

    // Get domain size (for MRV heuristic)
    size_t get_domain_size(Index index) const;

    // Place a piece and propagate constraints
    // Returns false if any domain becomes empty (inconsistency detected)
    bool place_piece(Index index, const RotatedPiece& piece);

    // Remove a piece and restore domains from snapshot
    void remove_piece(Index index);

    // Check if a piece is still available
    bool is_piece_available(int piece_index) const;

    // Mark piece as used/available
    void mark_piece_used(int piece_index);
    void mark_piece_available(int piece_index);

    // Save current state for backtracking
    void push_state();

    // Restore previous state
    void pop_state();

    // Get all unassigned positions
    std::vector<Index> get_unassigned_positions() const;

    // Get neighbors of a position (for constraint propagation)
    std::vector<Index> get_neighbor_indices(Index index) const;

    // Count unassigned neighbors (for degree heuristic)
    size_t count_unassigned_neighbors(Index index) const;

    // Board size - inline for hot path
    [[gnu::always_inline]] size_t board_size() const { return board_size_; }

    // Total positions - inline for hot path
    [[gnu::always_inline]] size_t total_positions() const { return board_size_ * board_size_; }

    // Check if all positions are assigned
    bool is_complete() const;

    // Get number of assigned positions
    [[gnu::always_inline]] size_t assigned_count() const { return assigned_count_; }

    // Get color frequency for rare color heuristic (lower = rarer)
    [[gnu::always_inline]] uint16_t get_color_frequency(PiecePart color) const {
        return (color < MAX_COLORS) ? color_frequency_[color] : max_color_frequency_;
    }
    [[gnu::always_inline]] uint16_t get_max_color_frequency() const { return max_color_frequency_; }

private:
    static constexpr size_t MAX_COLORS = 32;
    size_t board_size_;
    std::vector<Piece> pieces_;
    std::vector<DomainEntry> domains_;

    // Bitset for O(1) piece availability checks (replaces vector<bool>)
    std::bitset<MAX_PIECES> piece_availability_;

    // Trailing system for efficient backtracking
    std::vector<TrailEntry> trail_;
    std::vector<size_t> choice_points_;  // Stack of trail positions

    size_t assigned_count_ = 0;

    // OPTIMIZATION: Cached neighbor degrees for O(1) lookup in MRV degree heuristic
    // neighbor_degrees_[pos_1d] = count of unassigned adjacent positions
    // Updated incrementally when positions are assigned
    std::array<uint8_t, MAX_PIECES> neighbor_degrees_;

    // OPTIMIZATION: Color frequency for rare color elimination heuristic
    // color_frequency_[color] = count of edges with this color across all pieces
    // Lower frequency = rarer color, prioritize placing these pieces early
    std::array<uint16_t, MAX_COLORS> color_frequency_;
    uint16_t max_color_frequency_ = 0;  // For normalization

    // OPTIMIZATION: Reusable scratch buffers to avoid heap allocations on hot path
    // These are cleared and reused instead of creating new vectors each call
    mutable std::vector<RotatedPiece> scratch_removed_;
    mutable std::vector<RotatedPiece> scratch_removed_propagate_;

    // Convert 2D index to 1D - HOT PATH, always inline
    [[gnu::always_inline]] size_t to_1d(Index index) const { return index.second * board_size_ + index.first; }

    // Convert 1D index to 2D - inline for hot path
    [[gnu::always_inline]] Index to_2d(size_t index) const { return {index % board_size_, index / board_size_}; }

    // Check if index is valid - inline for hot path
    [[gnu::always_inline]] bool is_valid_index(Index index) const {
        return index.first < board_size_ && index.second < board_size_;
    }

    // Check if position is corner, edge, or interior - inline for hot path
    [[gnu::always_inline]] bool is_corner(Index index) const {
        return (index.first == 0 || index.first == board_size_ - 1) &&
               (index.second == 0 || index.second == board_size_ - 1);
    }
    [[gnu::always_inline]] bool is_edge(Index index) const {
        return !is_corner(index) &&
               (index.first == 0 || index.first == board_size_ - 1 ||
                index.second == 0 || index.second == board_size_ - 1);
    }
    [[gnu::always_inline]] bool is_interior(Index index) const {
        return !is_corner(index) && !is_edge(index);
    }

    // Compute initial domain for a position (based on position type)
    std::vector<RotatedPiece> compute_initial_domain(Index index) const;

    // Recompute domain for a position based on placed neighbors
    // Returns false if domain becomes empty
    bool recompute_domain(Index index, const RotatedPiece& placed_piece, Index placed_index);

    // Propagate constraints to all affected neighbors
    // Returns false if any domain becomes empty
    bool propagate_to_neighbors(Index placed_index, const RotatedPiece& placed_piece);

    // Get the edge constraint from a placed piece for a specific direction
    PiecePart get_edge_constraint(const RotatedPiece& piece, int direction) const;

    // Filter domain entries that don't match the constraint
    void filter_domain_by_constraint(Index index, int direction, PiecePart constraint);

    // Undo a single trail entry (called during pop_state)
    void undo_trail_entry(const TrailEntry& entry);

    // Record a domain shrink in the trail
    void record_domain_shrink(size_t position_1d, const std::vector<RotatedPiece>& removed);

    // Record piece used in the trail
    void record_piece_used(int piece_index);

    // Record position assigned in the trail
    void record_position_assigned(size_t position_1d);
};

} // namespace eternity2_v2

#endif // ETERNITY2_V2_DOMAIN_H
