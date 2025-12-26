//
// Value Ordering Heuristics Implementation
// LCV (Least Constraining Value)
//

#include "value_ordering.h"
#include <random>
#include <chrono>

using eternity2_common::Piece;
using eternity2_common::PiecePart;
using eternity2_common::WALL;
using eternity2_common::UP_MASK;
using eternity2_common::RIGHT_MASK;
using eternity2_common::DOWN_MASK;
using eternity2_common::LEFT_MASK;
using eternity2_common::rotate_piece_right;
using eternity2_common::get_piece_part;

namespace eternity2_v2 {

// Direction constants
constexpr int DIR_UP = 0;
constexpr int DIR_RIGHT = 1;
constexpr int DIR_DOWN = 2;
constexpr int DIR_LEFT = 3;

// Get the edge of a rotated piece in a specific direction
// OPTIMIZATION: Use cached edges instead of recomputing rotation
[[gnu::always_inline]] static inline PiecePart get_edge(const RotatedPiece& piece, int direction) {
    switch (direction) {
        case DIR_UP:    return piece.edge_up;
        case DIR_RIGHT: return piece.edge_right;
        case DIR_DOWN:  return piece.edge_down;
        case DIR_LEFT:  return piece.edge_left;
        default:        return EMPTY;
    }
}

// Count how many values in neighbor's domain would remain after placing this piece
static size_t count_compatible_values(
    const DomainEntry& neighbor_domain,
    int direction,  // Direction FROM the neighbor TO the placed piece
    PiecePart constraint,
    int placed_piece_index)
{
    if (neighbor_domain.is_assigned) return 0;  // Already assigned, doesn't count

    size_t count = 0;
    for (const auto& rp : neighbor_domain.valid_pieces) {
        // Skip if it's the same piece we're placing
        if (rp.index == placed_piece_index) continue;

        // Check if this value matches the constraint
        PiecePart edge = get_edge(rp, direction);
        if (edge == constraint) {
            count++;
        }
    }
    return count;
}

// Calculate rare color bonus: higher bonus for pieces with rarer colors
// This encourages placing rare-color pieces early to avoid stranding them later
[[gnu::always_inline]] static inline size_t calculate_rare_color_bonus(
    const DomainManager& domain_manager,
    const RotatedPiece& piece)
{
    uint16_t max_freq = domain_manager.get_max_color_frequency();
    if (max_freq == 0) return 0;

    // Sum up "rarity scores" for each edge (max_freq - freq = higher for rare colors)
    size_t bonus = 0;
    bonus += max_freq - domain_manager.get_color_frequency(piece.edge_up);
    bonus += max_freq - domain_manager.get_color_frequency(piece.edge_right);
    bonus += max_freq - domain_manager.get_color_frequency(piece.edge_down);
    bonus += max_freq - domain_manager.get_color_frequency(piece.edge_left);

    return bonus;
}

size_t calculate_constrainedness(
    const DomainManager& domain_manager,
    Index index,
    const RotatedPiece& piece)
{
    size_t total_remaining = 0;

    // Get edges of the piece we're considering placing
    PiecePart up_edge = get_edge(piece, DIR_UP);
    PiecePart right_edge = get_edge(piece, DIR_RIGHT);
    PiecePart down_edge = get_edge(piece, DIR_DOWN);
    PiecePart left_edge = get_edge(piece, DIR_LEFT);

    size_t board_size = domain_manager.board_size();

    // Check up neighbor (they need matching DOWN edge)
    if (index.second > 0) {
        Index up_idx = {index.first, index.second - 1};
        const DomainEntry& up_domain = domain_manager.get_domain(up_idx);
        if (!up_domain.is_assigned) {
            total_remaining += count_compatible_values(up_domain, DIR_DOWN, up_edge, piece.index);
        }
    }

    // Check right neighbor (they need matching LEFT edge)
    if (index.first < board_size - 1) {
        Index right_idx = {index.first + 1, index.second};
        const DomainEntry& right_domain = domain_manager.get_domain(right_idx);
        if (!right_domain.is_assigned) {
            total_remaining += count_compatible_values(right_domain, DIR_LEFT, right_edge, piece.index);
        }
    }

    // Check down neighbor (they need matching UP edge)
    if (index.second < board_size - 1) {
        Index down_idx = {index.first, index.second + 1};
        const DomainEntry& down_domain = domain_manager.get_domain(down_idx);
        if (!down_domain.is_assigned) {
            total_remaining += count_compatible_values(down_domain, DIR_UP, down_edge, piece.index);
        }
    }

    // Check left neighbor (they need matching RIGHT edge)
    if (index.first > 0) {
        Index left_idx = {index.first - 1, index.second};
        const DomainEntry& left_domain = domain_manager.get_domain(left_idx);
        if (!left_domain.is_assigned) {
            total_remaining += count_compatible_values(left_domain, DIR_RIGHT, left_edge, piece.index);
        }
    }

    return total_remaining;
}

std::vector<RotatedPiece> order_values_lcv(
    const DomainManager& domain_manager,
    Index index,
    const std::vector<RotatedPiece>& values)
{
    if (values.empty()) return values;

    // OPTIMIZATION: Lazy LCV - only compute scores for first K values
    // Most searches don't try all values before backtracking
    constexpr size_t K = 8;  // Only score first K values

    if (values.size() <= 3) {
        // For very small domains, full ordering isn't worth the overhead
        return values;
    }

    const size_t compute_count = std::min(values.size(), K);

    // Score first K values
    std::vector<ScoredPiece> scored;
    scored.reserve(compute_count);

    for (size_t i = 0; i < compute_count; ++i) {
        // Base LCV score: how many neighbor values remain (higher = less constraining)
        size_t score = calculate_constrainedness(domain_manager, index, values[i]);
        // NOTE: Rare color bonus disabled - adds overhead without clear benefit
        // size_t rare_bonus = calculate_rare_color_bonus(domain_manager, values[i]) / 8;
        // score += rare_bonus;
        scored.push_back({values[i], score});
    }

    // Sort scored portion (descending - higher score = less constraining)
    std::sort(scored.begin(), scored.end(),
        [](const ScoredPiece& a, const ScoredPiece& b) {
            return a.score > b.score;
        }
    );

    // Build result: sorted portion + remaining unsorted
    std::vector<RotatedPiece> result;
    result.reserve(values.size());

    for (const auto& sp : scored) {
        result.push_back(sp.piece);
    }
    for (size_t i = compute_count; i < values.size(); ++i) {
        result.push_back(values[i]);
    }

    return result;
}

std::vector<RotatedPiece> order_values_random(
    const std::vector<RotatedPiece>& values)
{
    std::vector<RotatedPiece> result = values;

    // Use random device for better randomness
    static thread_local std::mt19937 rng(
        std::chrono::steady_clock::now().time_since_epoch().count()
    );

    std::shuffle(result.begin(), result.end(), rng);

    return result;
}

std::vector<RotatedPiece> order_values_none(
    const std::vector<RotatedPiece>& values)
{
    return values;  // Return as-is
}

} // namespace eternity2_v2
