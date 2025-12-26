//
// Domain Manager for Maintaining Arc Consistency (MAC)
// solver_v2 - Optimized Eternity II Solver
//

#ifndef ETERNITY2_V2_DOMAIN_H
#define ETERNITY2_V2_DOMAIN_H

#include "../../solver/piece_search/piece_search.h"
#include "../../solver/board/board.h"

#include <vector>
#include <stack>
#include <bitset>
#include <functional>
#include <array>
#include <unordered_map>

namespace eternity2_v2 {

// Maximum pieces for Eternity II (256 pieces on 16x16 board)
static constexpr size_t MAX_PIECES = 256;

// Trail entry for incremental state management
// Instead of copying entire domain state, we record changes and undo them
struct TrailEntry {
    enum class Type {
        DOMAIN_SHRINK,      // Pieces were removed from a domain
        PIECE_USED,         // A piece was marked as used
        POSITION_ASSIGNED   // A position was marked as assigned
    };

    Type type;
    size_t position_1d;                        // Affected position (for DOMAIN_SHRINK, POSITION_ASSIGNED)
    int piece_index;                           // Affected piece index (for PIECE_USED)
    std::vector<RotatedPiece> removed_pieces;  // Pieces that were removed (for DOMAIN_SHRINK)
};

// Domain entry for a single board position
struct DomainEntry {
    std::vector<RotatedPiece> valid_pieces;  // Valid piece/rotation combinations
    bool is_assigned = false;                 // Whether this position has a placed piece

    size_t size() const { return valid_pieces.size(); }
    bool empty() const { return valid_pieces.empty(); }
};

// Compatibility entry: stores which pieces can be adjacent in each direction
// Key: (piece_index, rotation, direction) -> vector of compatible (piece_index, rotation)
using CompatiblePieces = std::vector<std::pair<int, int>>;

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

    // Board size
    size_t board_size() const { return board_size_; }

    // Total positions
    size_t total_positions() const { return board_size_ * board_size_; }

    // Check if all positions are assigned
    bool is_complete() const;

    // Get number of assigned positions
    size_t assigned_count() const { return assigned_count_; }

private:
    size_t board_size_;
    std::vector<Piece> pieces_;
    std::vector<DomainEntry> domains_;

    // Bitset for O(1) piece availability checks (replaces vector<bool>)
    std::bitset<MAX_PIECES> piece_availability_;

    // Trailing system for efficient backtracking
    std::vector<TrailEntry> trail_;
    std::vector<size_t> choice_points_;  // Stack of trail positions

    size_t assigned_count_ = 0;

    // Piece compatibility matrix for O(1) constraint lookups
    // compatible_[piece_idx][rotation][direction] = vector of (piece_idx, rotation)
    // direction: 0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
    std::vector<std::array<std::array<CompatiblePieces, 4>, 4>> compatible_;
    bool compatibility_computed_ = false;

    // Convert 2D index to 1D
    size_t to_1d(Index index) const;

    // Convert 1D index to 2D
    Index to_2d(size_t index) const;

    // Check if index is valid
    bool is_valid_index(Index index) const;

    // Check if position is corner, edge, or interior
    bool is_corner(Index index) const;
    bool is_edge(Index index) const;
    bool is_interior(Index index) const;

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

    // Precompute piece compatibility matrix for O(1) constraint lookups
    void precompute_compatibility();

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
