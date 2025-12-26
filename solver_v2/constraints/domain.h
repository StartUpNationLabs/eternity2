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
#include <functional>

namespace eternity2_v2 {

// Domain entry for a single board position
struct DomainEntry {
    std::vector<RotatedPiece> valid_pieces;  // Valid piece/rotation combinations
    bool is_assigned = false;                 // Whether this position has a placed piece

    size_t size() const { return valid_pieces.size(); }
    bool empty() const { return valid_pieces.empty(); }
};

// Snapshot of domains for backtracking
struct DomainSnapshot {
    std::vector<DomainEntry> domains;
    std::vector<bool> piece_availability;
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
    std::vector<bool> piece_availability_;
    std::stack<DomainSnapshot> state_stack_;
    size_t assigned_count_ = 0;

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
};

} // namespace eternity2_v2

#endif // ETERNITY2_V2_DOMAIN_H
