//
// Optimized Piece Search Implementation
//

#include "piece_search_optimized.h"
#include "common/types.h"
#include "common/piece_utils.h"
#include <algorithm>

using eternity2_common::rotate_piece_right;

namespace eternity2 {

std::vector<PieceRotationsWAvailability>
prepare_pieces_for_simd(const std::vector<Piece>& pieces) {
    std::vector<PieceRotationsWAvailability> result;
    result.reserve(pieces.size());

    for (size_t i = 0; i < pieces.size(); ++i) {
        PieceRotationsWAvailability p;
        p.index = static_cast<int>(i);
        p.available = true;

        // Pre-compute all 4 rotations
        for (int rot = 0; rot < 4; ++rot) {
            p.rotations[rot] = rotate_piece_right(pieces[i], rot);
        }

        result.push_back(p);
    }

    return result;
}

std::vector<RotatedPiece> match_piece_mask_simd(
    const std::vector<Query>& queries,
    const std::vector<PieceRotationsWAvailability>& pieces)
{
    std::vector<RotatedPiece> results;
    results.reserve(pieces.size() * 4);  // Worst case: all pieces in all rotations

    // Process each piece
    for (size_t i = 0; i < pieces.size(); ++i) {
        if (!pieces[i].available) continue;

        // Try each of the 4 rotations
        for (int rot = 0; rot < 4; ++rot) {
            Piece rotated = pieces[i].rotations[rot];
            bool keep = true;

            // Apply all query constraints
            // CRITICAL: Preserve correct NEGATIVE/POSITIVE query semantics
            for (const auto& query : queries) {
                // Check if this rotated piece matches the query
                bool match = match_piece_mask_internal(query.piece, query.mask, rotated);

                // NEGATIVE query semantics (CRITICAL - this is what solver_v2 got wrong):
                // - NEGATIVE means "exclude pieces that MATCH the pattern"
                // - Used for wall exclusion: "exclude pieces with walls on this edge"
                // - Example: if neighbor exists on right, NEGATIVE query with FULLWALL/RIGHT_MASK
                //   excludes pieces that have a wall on the right edge
                //
                // POSITIVE query semantics:
                // - POSITIVE means "include only pieces that MATCH the pattern"
                // - Used for pattern matching: "must have this specific edge pattern"
                //
                // If NEGATIVE query and piece MATCHES => EXCLUDE (keep = false)
                // If NEGATIVE query and piece DOESN'T match => INCLUDE (keep = true)
                // If POSITIVE query and piece MATCHES => INCLUDE (keep = true)
                // If POSITIVE query and piece DOESN'T match => EXCLUDE (keep = false)

                if (query.type == QueryType::POSITIVE && !match) {
                    keep = false;
                    break;  // Fail fast - this rotation doesn't match
                }
                if (query.type == QueryType::NEGATIVE && match) {
                    keep = false;
                    break;  // Fail fast - this rotation is excluded
                }
            }

            if (keep) {
                // Store the ORIGINAL piece (not rotated), along with the rotation
                results.push_back({
                    pieces[i].rotations[0],  // Original piece (rotation 0)
                    rot,                      // Rotation that worked
                    pieces[i].index           // Original index
                });
            }
        }
    }

    return results;
}

#ifdef DEBUG
bool verify_match_piece_mask(
    const std::vector<Query>& queries,
    const std::vector<PieceWAvailability>& pieces_scalar,
    const std::vector<PieceRotationsWAvailability>& pieces_simd)
{
    // Get results from both implementations
    auto scalar_result = match_piece_mask(queries, pieces_scalar);
    auto simd_result = match_piece_mask_simd(queries, pieces_simd);

    // Results must have the same size
    if (scalar_result.size() != simd_result.size()) {
        return false;
    }

    // Sort both results for comparison (order doesn't matter, content does)
    auto compare = [](const RotatedPiece& a, const RotatedPiece& b) {
        if (a.index != b.index) return a.index < b.index;
        return a.rotation < b.rotation;
    };

    std::sort(scalar_result.begin(), scalar_result.end(), compare);
    std::sort(simd_result.begin(), simd_result.end(), compare);

    // Compare each result
    for (size_t i = 0; i < scalar_result.size(); ++i) {
        if (scalar_result[i].index != simd_result[i].index ||
            scalar_result[i].rotation != simd_result[i].rotation) {
            return false;
        }
    }

    return true;
}
#endif

} // namespace eternity2
