//
// Optimized Piece Search with SIMD Acceleration
//

#ifndef ETERNITY2_PIECE_SEARCH_OPTIMIZED_H
#define ETERNITY2_PIECE_SEARCH_OPTIMIZED_H

#include "piece_search.h"
#include "../simd/simd_ops.h"
#include <vector>

namespace eternity2 {

// Pre-computed rotations for SIMD batch processing
// Stores all 4 rotations of a piece in aligned memory for cache efficiency
struct alignas(ETERNITY2_SIMD_ALIGNMENT) PieceRotationsWAvailability {
    Piece rotations[4];  // All 4 rotations pre-computed
    int index;           // Original piece index
    bool available;      // Availability flag

    PieceRotationsWAvailability() : rotations{}, index(-1), available(true) {}
};

// Convert standard pieces to rotation-cached format
// Pre-computes all rotations to avoid repeated rotation calculations
std::vector<PieceRotationsWAvailability>
prepare_pieces_for_simd(const std::vector<Piece>& pieces);

// SIMD-optimized version of match_piece_mask
// CRITICAL: Preserves NEGATIVE query semantics for wall exclusion
// This is the key function that solver_v2 got wrong
std::vector<RotatedPiece> match_piece_mask_simd(
    const std::vector<Query>& queries,
    const std::vector<PieceRotationsWAvailability>& pieces);

#ifdef DEBUG
// Verification function - compares SIMD result with scalar
// Use in DEBUG builds to catch optimization bugs
bool verify_match_piece_mask(
    const std::vector<Query>& queries,
    const std::vector<PieceWAvailability>& pieces_scalar,
    const std::vector<PieceRotationsWAvailability>& pieces_simd);
#endif

} // namespace eternity2

#endif // ETERNITY2_PIECE_SEARCH_OPTIMIZED_H
