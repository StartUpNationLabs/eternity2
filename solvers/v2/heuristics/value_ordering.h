//
// Value Ordering Heuristics for solver_v2
// Implements LCV (Least Constraining Value)
//

#ifndef ETERNITY2_V2_VALUE_ORDERING_H
#define ETERNITY2_V2_VALUE_ORDERING_H

#include "../constraints/domain.h"
#include <vector>
#include <algorithm>

namespace eternity2_v2 {

// Piece with its constrainedness score
struct ScoredPiece {
    RotatedPiece piece;
    size_t score;  // Higher = less constraining = better
};

// Order values using LCV (Least Constraining Value) heuristic
// Returns pieces sorted by how many options they leave for neighbors
// Pieces that leave more options are tried first
std::vector<RotatedPiece> order_values_lcv(
    const DomainManager& domain_manager,
    Index index,
    const std::vector<RotatedPiece>& values);

// Random ordering (for comparison with v1)
std::vector<RotatedPiece> order_values_random(
    const std::vector<RotatedPiece>& values);

// No ordering (original order)
std::vector<RotatedPiece> order_values_none(
    const std::vector<RotatedPiece>& values);

// Calculate how constraining a piece placement would be
// Higher score = less constraining = more options left for neighbors
size_t calculate_constrainedness(
    const DomainManager& domain_manager,
    Index index,
    const RotatedPiece& piece);

} // namespace eternity2_v2

#endif // ETERNITY2_V2_VALUE_ORDERING_H
